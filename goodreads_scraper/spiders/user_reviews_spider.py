"""Spider to extract information from a /author/show page"""
import logging
import re

import scrapy
from scrapy import Request

from ..items import UserReviewLoader, UserReviewItem

logger = logging.getLogger(__name__)
USER_ID_NAME_EXTRACTOR = re.compile(".*/user/show/(.*$)")
USER_ID_EXTRACTOR = re.compile(".*review/list/(.*)\?")
# For whatever reason, goodreads refuses to give scrapy more than 30 results per page to scrapers
ITEMS_PER_PAGE = 30


class UserReviewsSpider(scrapy.Spider):
    name = "user_reviews"
    custom_settings = {'ITEM_PIPELINES': {'goodreads_scraper.pipelines.PubsubPipeline': 400}}

    def __init__(self, profiles, project_id="test-project", topic_name="test-topic", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_settings['GCP_PROJECT_ID'] = project_id
        self.custom_settings['PUBSUB_TOPIC_NAME'] = topic_name
        self.start_urls = profiles

    def start_requests(self):
        for user_id in self.start_urls:
            converted_url = self.format_review_url(user_id, 1)
            yield Request(converted_url, callback=self.parse, dont_filter=True, meta={"user_id": user_id, "page": 1})

    def parse(self, response):
        user_id = response.meta.get("user_id")
        review_blocks = response.xpath('//tr[@class="bookalike review"]')

        reviews_yielded = 0
        # When you scrape goodreads for whatever reason they put on infinite scroll, which causes them to return
        # unpredictable numbers of reviews, and might cause problems when you paginate
        for review_block in review_blocks[:ITEMS_PER_PAGE]:
            goodreads_rating = review_block.xpath(
                'td[@class="field rating"]//div[@class="value"]//span[@class=" staticStars notranslate"]/@title').get()
            user_rating = self.convert_goodreads_ratings_to_star_count(goodreads_rating)
            if goodreads_rating and user_rating > 0:
                reviews_yielded += 1
                yield self.build_review(review_block, user_id, user_rating)

        if reviews_yielded == ITEMS_PER_PAGE:
            new_page_count = response.meta.get("page") + 1
            formatted_url = self.format_review_url(user_id, new_page_count)
            yield Request(formatted_url, callback=self.parse, dont_filter=True,
                          meta={"user_id": user_id, "page": new_page_count})

    @staticmethod
    def convert_goodreads_ratings_to_star_count(goodreads_rating):
        ratings_dict = {
            "it was amazing": 5,
            "really liked it": 4,
            "liked it": 3,
            "it was ok": 2,
            "did not like it": 1,
        }
        return ratings_dict.get(goodreads_rating)

    @staticmethod
    def build_review(review_block, user_id, user_rating):
        loader = UserReviewLoader(UserReviewItem(), review_block)
        loader.add_value('user_id', user_id)

        loader.add_xpath('book_id', 'td[@class="field cover"]//div//div/@data-resource-id')
        loader.add_xpath('book_url', 'td[@class="field title"]//a/@href')
        loader.add_xpath('book_name', 'td[@class="field title"]//a/@title')

        loader.add_xpath('date_read', 'td[@class="field date_read"]//div[@class="value"]//div//div//span/text()')
        loader.add_xpath('date_added', 'td[@class="field date_added"]//div[@class="value"]//span/@title')

        loader.add_value('user_rating', user_rating)
        return loader.load_item()

    @staticmethod
    def format_review_url(user_id_and_name, page):
        return f"https://www.goodreads.com/review/list/{user_id_and_name}?shelf=read&sort=rating&page={page}&per_page={ITEMS_PER_PAGE}"

    @staticmethod
    def extract_username_from_url(url):
        username = re.findall(USER_ID_NAME_EXTRACTOR, url)
        return username[0] if username else None
