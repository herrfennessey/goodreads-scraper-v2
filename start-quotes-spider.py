from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from goodreads_scraper.spiders import TestSpider

process = CrawlerProcess(get_project_settings())
process.crawl(TestSpider)
process.start()
