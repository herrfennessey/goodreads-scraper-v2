# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html
import re
from datetime import datetime

import scrapy
from dateutil.parser import parse
from itemloaders import ItemLoader
from itemloaders.processors import MapCompose, TakeFirst
from scrapy import Field


def safe_parse_date(date):
    try:
        date = parse(date, fuzzy=True, default=datetime.min)
        date = date.isoformat()
    except ValueError:
        date = None
    return date


class UserReviewItem(scrapy.Item):
    user_id = Field()
    work_id = Field()

    book_id = Field()
    book_url = Field()
    book_name = Field()

    date_read = Field(input_processor=MapCompose(safe_parse_date))
    date_added = Field(input_processor=MapCompose(safe_parse_date))

    user_rating = Field(serializer=int)


class UserReviewLoader(ItemLoader):
    default_output_processor = TakeFirst()
