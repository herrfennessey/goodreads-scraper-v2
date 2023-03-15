"""Spider to extract information from a /author/show page"""
import logging
import re
from urllib.parse import urljoin

import scrapy
from scrapy import Request

from goodreads_scraper.items import UserProfileItem

logger = logging.getLogger(__name__)

BOOKS_READ_REGEX = re.compile(r".*\b(\d+)\sbooks")
PROFILE_ID_REGEX = re.compile(r".*goodreads.com\/user\/show\/([0-9]*).*")
BOOKS_FOLLOW_THRESHOLD = 50
GOODREADS_URL_PREFIX = "https://www.goodreads.com"


class FriendNetworkSpider(scrapy.Spider):
    name = "friend_network"
    custom_settings = {'CLOSESPIDER_ITEMCOUNT': 50,
                       'ITEM_PIPELINES': {'goodreads_scraper.pipelines.PubsubPipeline': 400}}

    def __init__(self, start_profile_id: str, project_id: str = None, topic_name: str = None, *args, **kwargs):
        """
        :param books: comma delimited list of goodreads book IDs
        :param project_id: (Optional) GCP project ID
        :param topic_name: (Optional) GCP Pub/Sub topic name
        """
        super().__init__(*args, **kwargs)
        if project_id and topic_name:
            self.custom_settings["GCP_PROJECT_ID"] = project_id
            self.custom_settings["PUBSUB_TOPIC_NAME"] = topic_name
        self.profile_id = start_profile_id

    def start_requests(self):
        converted_url = self.format_profile_url(self.profile_id)
        yield Request(converted_url, callback=self.parse, dont_filter=True)

    def parse(self, response, **kwargs):
        # Don't scrape author pages, it's too annoying to get their read list
        if not response.url.startswith("https://www.goodreads.com/user/show/"):
            logger.debug(f"skipping page {response.url}")
            return

        yield self.parse_user_profile(response.url)
        for friend_block in response.xpath('//div[@class="left"]'):
            friend_url = urljoin(GOODREADS_URL_PREFIX, friend_block.xpath('div[@class="friendName"]//a/@href').get())
            friend_count = self.extract_friend_count(friend_block)
            if friend_count > BOOKS_FOLLOW_THRESHOLD:
                yield Request(friend_url, callback=self.parse)

    @staticmethod
    def extract_friend_count(selector_block):
        friend_count = 0
        for div_text in selector_block.xpath('text()').getall():
            regex_results = re.findall(BOOKS_READ_REGEX, div_text)
            if len(regex_results) > 0:
                friend_count = int(regex_results[0])
        return friend_count

    @staticmethod
    def format_profile_url(user_id):
        return f"https://www.goodreads.com/user/show/{user_id}"

    @staticmethod
    def parse_user_profile(url):
        regex_results = re.findall(PROFILE_ID_REGEX, url)
        if len(regex_results) > 0:
            return UserProfileItem({"user_id": regex_results[0]})

