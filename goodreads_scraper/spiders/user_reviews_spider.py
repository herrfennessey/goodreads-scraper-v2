"""Spider to extract information from a /author/show page"""
import logging
import re
import time

import scrapy
from scrapy import Request

from ..items import UserReviewLoader, UserReviewItem

logger = logging.getLogger(__name__)
USER_ID_NAME_EXTRACTOR = re.compile(".*/user/show/(.*$)")
USER_ID_EXTRACTOR = re.compile(".*review/list/(.*)\?")
ITEMS_PER_PAGE = 200
MAX_PAGE_COUNT = 60


class UserReviewsSpider(scrapy.Spider):
    name = "user_reviews"
    custom_settings = {'ITEM_PIPELINES': {'goodreads_scraper.pipelines.PubsubPipeline': 400}}

    def __init__(self, profiles, project_id=None, topic_name=None, *args, **kwargs):
        """
        :param profiles: comma delimited list of goodreads profile IDs
        :param project_id: (Optional) GCP project ID
        :param topic_name: (Optional) GCP Pub/Sub topic name
        """
        super().__init__(*args, **kwargs)
        if project_id and topic_name:
            self.custom_settings["GCP_PROJECT_ID"] = project_id
            self.custom_settings["PUBSUB_TOPIC_NAME"] = topic_name
        self.start_urls = profiles.split(",")

    def start_requests(self):
        for user_id in self.start_urls:
            converted_url = self.format_review_url(user_id, 1)
            yield Request(converted_url, callback=self.parse, dont_filter=True, meta={"user_id": user_id, "page": 1})

    def parse(self, response):
        reviews_yielded = 0
        user_id = response.meta.get("user_id")
        for post in response.xpath('//channel/item'):
            loader = UserReviewLoader(UserReviewItem(), post)

            user_rating = post.xpath('user_rating/text()').get()
            if user_rating and int(user_rating) == 0:
                continue

            loader.add_value('user_rating', user_rating)
            loader.add_value('user_id', user_id)
            loader.add_xpath('book_id', 'book_id/text()')
            loader.add_value('scrape_time', round(time.time() * 1000))

            user_read_at = post.xpath('user_read_at/text()').get()
            if user_read_at:
                loader.add_value('date_read', user_read_at)
            else:
                loader.add_xpath('date_read', 'user_date_added/text()')

            reviews_yielded += 1
            yield loader.load_item()

        if reviews_yielded == ITEMS_PER_PAGE:
            new_page_count = response.meta.get("page") + 1
            if new_page_count > MAX_PAGE_COUNT:
                logger.warning(f"Reached max page count for user {user_id}")
                return
            else:
                formatted_url = self.format_review_url(user_id, new_page_count)
                yield Request(formatted_url, callback=self.parse, dont_filter=True,
                              meta={"user_id": user_id, "page": new_page_count})


    @staticmethod
    def format_review_url(user_id_and_name, page):
        return f"https://www.goodreads.com/review/list_rss/{user_id_and_name}?shelf=read&order=d&sort=rating&per_page={ITEMS_PER_PAGE}&page={page}"