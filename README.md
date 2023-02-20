# goodreads-scraper-v2

## Introduction

This is a Python + Scrapy (+ Selenium) based web crawler that fetches book and author data from Goodreads. This can be
used for collecting a large data set in a short period of time, for a data analysis/visualization project.

It uses `scrapyrt` to expose the Scrapy API over HTTP. This allows you to run the crawler in a Docker container and
access it from a remote machine.

Be careful with hitting this API too often, as you will get IP banned. 

## Installation

1. Install Python 3.6 or higher
2. Install python dependencies: `pip install -r requirements.txt`

## Usage

1. Run the scraper webservice: `scrapyrt -p 9080`
2. Hit the API: 

