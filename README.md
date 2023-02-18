# goodreads-scraper-v2

## Introduction

This is a Python + Scrapy (+ Selenium) based web crawler that fetches book and author data from Goodreads. This can be used for collecting a large data set in a short period of time, for a data analysis/visualization project.

With appropriate controls, the crawler can collect metadata for ~50 books per minute (~3000 per hour). If you want to be more aggressive (at the risk of getting your IP blocked by Goodreads), you can set the `DOWNLOAD_DELAY` to a smaller value in [`settings.py`](./GoodreadsScraper/settings.py#L30), but this is not recommended.
