"""Spider to extract information from a /book/show type page on Goodreads"""
import json
import re
import time
from typing import Dict, List
from urllib.parse import urlsplit

import isbnlib
import scrapy
from scrapy import Request

from ..items import BookLoader, BookItem

TYPENAME = "__typename"


class BookSpider(scrapy.Spider):
    """Extract information from a /book/show type page on Goodreads"""
    name = "book"
    custom_settings = {'ITEM_PIPELINES': {'goodreads_scraper.pipelines.PubsubPipeline': 400}}

    def __init__(self, books: List[str], project_id: str, topic_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_settings['GCP_PROJECT_ID'] = project_id
        self.custom_settings['PUBSUB_TOPIC_NAME'] = topic_name
        self.start_urls = books

    def start_requests(self):
        for book_id in self.start_urls:
            converted_url = self._generate_book_url(book_id)
            yield Request(converted_url, callback=self.parse, dont_filter=True)

    def parse(self, response):
        self.logger.info("New Book Response")
        return self.parse_book(response)

    def parse_book(self, response, loader=None):
        if not loader:
            loader = BookLoader(BookItem(), response=response)

        text_body = response.xpath('//*[@id="__NEXT_DATA__"]/text()').get()
        parsed_json_body = json.loads(text_body)
        book_info = parsed_json_body['props']['pageProps']['apolloState']

        contributor = self._take_largest_element(book_info, "Contributor")
        series = self._take_first_element(book_info, "Series")
        work = self._take_largest_element(book_info, "Work")
        book = self._take_largest_element(book_info, "Book")

        if not book:
            self.logger.warning("Unable to load book, skipping!")
            return

        book_details = book.get("details")

        backup_isbns = self._extract_isbn_from_affiliates(
            book.get("links({})", {}).get("secondaryAffiliateLinks", list()))

        book_url = urlsplit(response.request.url).path

        # High Level Info
        loader.add_value('book_id', book.get("legacyId"))
        loader.add_value('book_url', book_url)
        loader.add_value('book_title', book.get("title"))
        loader.add_value('author', contributor.get("name"))
        loader.add_value('author_url', contributor.get("webUrl"))
        loader.add_value('book_description', book.get('description({"stripped":true})'))
        loader.add_value('scrape_time', round(time.time() * 1000))

        # Work Details
        loader.add_value('work_internal_id', work.get("id"))
        loader.add_value('work_id', work.get("legacyId"))
        loader.add_value('publish_date', work.get("details").get("publicationTime"))
        loader.add_value('original_title', work.get("details").get("originalTitle"))

        # Work Statistics
        loader.add_value('num_ratings', work.get("stats").get("ratingsCount"))
        loader.add_value('num_reviews', work.get("stats").get("textReviewsCount"))
        loader.add_value('avg_rating', work.get("stats").get("averageRating"))
        loader.add_value('rating_histogram', work.get("stats").get("ratingsCountDist"))

        # Book Statistics
        loader.add_value('num_pages', book_details.get("numPages"))
        loader.add_value('language', book_details.get("language").get("name"))
        loader.add_value('asin', book_details.get("asin"))
        loader.add_value('series', series.get("title") if series else "")
        loader.add_value('genres', self._parse_genres(book.get("bookGenres")))

        # ISBN requires a bit of wrangling
        isbn = book_details.get("isbn") if book_details.get("isbn") else backup_isbns.get("isbn")
        isbn13 = book_details.get("isbn13") if book_details.get("isbn13") else backup_isbns.get("isbn13")
        loader.add_value('isbn', isbn)
        loader.add_value('isbn13', isbn13)

        return loader.load_item()

    def _take_largest_element(self, input_dict, element_type):
        largest = None
        for block in input_dict.values():
            if block.get(TYPENAME, "") == element_type:
                if largest is None:
                    largest = block
                else:
                    key_count = self._count_keys_recursive(block)
                    largest_count = self._count_keys_recursive(largest)
                    if key_count > largest_count:
                        largest = block
            else:
                continue
        return largest

    def _parse_genres(self, genre_input_list):
        parsed_genres = []
        for genre in genre_input_list:
            if genre.get(TYPENAME) == "BookGenre":
                genre_dict = genre.get("genre")
                if genre_dict.get(TYPENAME) == "Genre":
                    parsed_genres.append(genre_dict.get("name"))
        return parsed_genres

    def _take_first_element(self, input_dict, element_type):
        for block in input_dict.values():
            if block.get(TYPENAME, "") == element_type:
                return block

    def _count_keys_recursive(self, input_dict, counter=0):
        for each_key in input_dict:
            if isinstance(input_dict[each_key], dict):
                # Recursive call
                counter = self._count_keys_recursive(input_dict[each_key], counter + 1)
            else:
                counter += 1
        return counter

    @staticmethod
    def _generate_book_url(book_id):
        return f"https://www.goodreads.com/book/show/{book_id}"

    @staticmethod
    def _extract_isbn_from_affiliates(affiliates: List[Dict]) -> Dict[str, str]:
        """
        Amazon hates to leave money on the table, so if the book doesn't specifically have an ISBN such as a kindle
        edition of a book, they'll always try and tie it to a print version of the book with the affiliate links. We
        can use these affiliates to mine the ISBN and return it with the object

        :param affiliates: List of affiliate dictionaries containing their referral link (which contains ISBN)
        :return: A dictionary which returns ISBN and ISBN13 if found
        """
        isbn_dict = {
            "isbn": None,
            "isbn13": None
        }

        for affiliate in affiliates:
            match affiliate.get("name"):
                case "Barnes & Noble":
                    regex = r"https?:\/\/www\.barnesandnoble\.com\/w\/\?ean=(?P<isbn>[0-9A-Z]{10,13})$"
                case "Apple Books":
                    regex = r"https?:\/\/geo\.itunes\.apple\.com\/us\/book\/isbn(?P<isbn>[0-9A-Z]{10,13})\?.*"
                case "Google Play":
                    regex = r"https?:\/\/play\.google\.com\/store\/search\?q=(?P<isbn>[0-9A-Z]{10,13})&.*"
                case "Book Depository":
                    regex = r"https?:\/\/www\.bookdepository\.com\/search\?searchTerm=(?P<isbn>[0-9A-Z]{10,13})&.*"
                case "Indigo":
                    regex = r"https?:\/\/www\.chapters\.indigo\.ca\/en-ca\/home\/search\/\?keywords=(?P<isbn>[0-9A-Z]{10,13}).*"
                case _:
                    continue

            results = re.search(regex, affiliate["url"])
            # The regex messed up, or we weren't able to find an ISBN - just skip it
            if not results:
                continue

            regex_results = results.groupdict()

            if "isbn" in regex_results:
                extracted_isbn = regex_results["isbn"]

                if isbn_dict["isbn"] is None and len(extracted_isbn) == 10 and isbnlib.is_isbn10(extracted_isbn):
                    isbn_dict["isbn"] = extracted_isbn
                elif isbn_dict["isbn13"] is None and len(extracted_isbn) == 13 and isbnlib.is_isbn13(extracted_isbn):
                    isbn_dict["isbn13"] = extracted_isbn

            if isbn_dict["isbn13"] and isbn_dict["isbn"]:
                # We've filled both entries, no need to go further
                break

        return isbn_dict
