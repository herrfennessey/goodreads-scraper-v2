# -*- coding: utf-8 -*-
import json
import logging
from concurrent import futures
from typing import Callable

from google.cloud import pubsub_v1
from scrapy import signals

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

logger = logging.getLogger(__name__)


class PubsubPipeline(object):
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def __init__(self, crawler):
        self.publisher = None
        self.topic_path = None
        crawler.signals.connect(self.spider_opened, signal=signals.spider_opened)

    def spider_opened(self, spider):
        self.publisher = pubsub_v1.PublisherClient()
        project_id = spider.custom_settings.get("GCP_PROJECT_ID")
        topic_name = spider.custom_settings.get("PUBSUB_TOPIC_NAME")
        self.topic_path = self.publisher.topic_path(project_id, topic_name)

    def process_item(self, item, spider):
        publish_futures = []

        data = str(json.dumps(dict(item)))
        publish_future = self.publisher.publish(self.topic_path, data=data.encode("utf-8"))
        publish_future.add_done_callback(self.get_callback(publish_future, data))
        publish_futures.append(publish_future)

        futures.wait(publish_futures, return_when=futures.ALL_COMPLETED)
        return item

    @staticmethod
    def get_callback(
            publish_future: pubsub_v1.publisher.futures.Future, data: str
    ) -> Callable[[pubsub_v1.publisher.futures.Future], None]:
        """
        Taken from the GCP documentation page on publishing to PubSub topics. I have no idea what this code monstrosity
        is doing...
        https://cloud.google.com/pubsub/docs/publisher
        """

        def callback(publish_future: pubsub_v1.publisher.futures.Future) -> None:
            try:
                # Wait 60 seconds for the publish call to succeed.
                logger.info(publish_future.result(timeout=60))
            except futures.TimeoutError:
                logger.info(f"Publishing {data} timed out.")

        return callback
