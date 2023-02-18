from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from goodreads_scraper.goodreads_scraper.spiders.test_spider import TestSpider

process = CrawlerProcess(get_project_settings())
process.crawl(TestSpider)
process.start()
