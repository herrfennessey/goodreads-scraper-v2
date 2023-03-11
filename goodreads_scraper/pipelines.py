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
        project_id = spider.custom_settings.get("GCP_PROJECT_ID")
        topic_name = spider.custom_settings.get("PUBSUB_TOPIC_NAME")
        if project_id and topic_name:
            self.publisher = pubsub_v1.PublisherClient()
            self.topic_path = self.publisher.topic_path(project_id, topic_name)
        else:
            # For whatever reason, you can't modify the pipelines at __init__ parameters in the spider, so I have to
            # short circuit the initialization of the GCP subscriber, and also skip the pipeline on each item
            logger.warning("GCP_PROJECT_ID and PUBSUB_TOPIC_NAME must be set in order to use the PubsubPipeline.")

    def process_item(self, item, spider):
        # If the publisher or topic_path are not set, then we don't have a valid PubSub topic to publish to, so let's
        # break out early
        if not self.publisher or not self.topic_path:
            logging.info("Skipping pub/sub pipeline")
            return item

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
