# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html
import json
import re
from datetime import datetime

import isbnlib
import scrapy
from dateutil.parser import parse
from itemloaders import ItemLoader
from itemloaders.processors import MapCompose, TakeFirst, Compose
from scrapy import Field


def safe_parse_date(date):
    try:
        date = parse(date, fuzzy=True, default=datetime.min)
        date = date.isoformat()
    except ValueError:
        date = None
    return date


def convert_epoch_to_date(epoch):
    epoch_seconds = epoch / 1000
    time_object = datetime.fromtimestamp(epoch_seconds)
    return time_object.date().isoformat()

def convert_epoch_to_timestamp(epoch):
    epoch_seconds = epoch / 1000
    time_object = datetime.fromtimestamp(epoch_seconds)
    return time_object.isoformat()

def filter_asin(asin):
    if asin and len(str(asin)) == 10:
        return asin
    return None


def isbn_filter(isbn):
    if isbn and isbnlib.is_isbn10(isbn):
        return isbn


def isbn13_filter(isbn):
    if isbn and isbnlib.is_isbn13(isbn):
        return isbn


class BookLoader(ItemLoader):
    default_output_processor = TakeFirst()


class BookItem(scrapy.Item):
    # High Level Info
    book_id = Field(serializer=int)
    book_url = Field()
    book_title = Field(input_processor=MapCompose(str.strip))
    author = Field(input_processor=MapCompose(str.strip))
    author_url = Field(input_processor=MapCompose(str.strip))
    book_description = Field()
    scrape_time = Field(input_processor=MapCompose(convert_epoch_to_timestamp))

    # Work Details
    work_internal_id = Field()
    work_id = Field(serializer=int)
    publish_date = Field(input_processor=MapCompose(convert_epoch_to_date))
    original_title = Field(input_processor=MapCompose(str.strip))

    # Work Statistics
    num_ratings = Field()
    num_reviews = Field()
    avg_rating = Field()
    rating_histogram = Field(output_processor=Compose(list))

    # Book Statistics
    num_pages = Field()
    language = Field(input_processor=MapCompose(str.strip))
    isbn = Field(input_processor=MapCompose(str.strip, isbn_filter))
    isbn13 = Field(input_processor=MapCompose(str.strip, isbn13_filter))
    asin = Field(input_processor=MapCompose(filter_asin))
    series = Field(input_processor=MapCompose(str.strip))
    genres = Field(output_processor=Compose(set, list))



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
