# goodreads-scraper-v2

## Introduction

This is a Python + Scrapy (+ Selenium) based web crawler that fetches book and author data from Goodreads. This can be
used for collecting a large data set in a short period of time, for a data analysis/visualization project.

It uses `scrapyrt` to expose the Scrapy API over HTTP. ScrapyRT certainly isn't as robust as normal APIs we write, but
it does the job for this project. It also uses Google Cloud PubSub to sink all data into a message queue, which can be
processed asynchronously by cloud run services.

Be careful with hitting this API too often, as you will get IP banned.

## Installation

1. Clone the repo
2. Create a virtual environment: `python3 -m venv venv`
3. Activate the virtual environment: `source venv/bin/activate`
4. Install the requirements: `pip install -r requirements.txt`

## Usage

1. Run the scraper webservice: `scrapyrt -p 9080`
2. Start up the pubsub emulator in docker compose: `docker-compose up pubsub`
3. For your convenience, there are some scripts in the `scripts` directory which will help you set up pubsub and get it
   ready to be listened to.
    1. The first script is `load_local_topics_subscribers.py`. This script requires pubsub libraries in python, so it
       should be run with the virtual environment activated (`source venv/bin/activate`)
    2. The second script is `listen_to_topic.py` which will listen to all messages for 60 seconds. This script also
       requires pubsub libraries and should be run with your environment activated.

## API Endpoints

`crawl.json`

1. The API endpoint we are hitting is called crawl.json. You POST your request to it, and it will kick off a scraper
   process behind the scenes. The output of this topic is a pubsub topic, which must be passed in as a crawl argument.
2. Here is an example POST body for the book crawler which will query for books with IDs 15 and 14 and output the data
   to pubsub topic `test-topic` in project `test-project`:

   ```json
   {
    "spider_name": "book",
    "start_requests": true,
    "crawl_args": {
        "books": "15,14",
        "project_id": "test-project",
        "topic_name": "test-topic"
    }
   }
   ```
3. You can also remove the project ID and topic name if you do not want to output it to the pubsub topic. In this case,
   the output will only be returned in the response body.

## Debugging

1. You can run spiders locally by using the `scrapy crawl` command. For example, to run the book spider, you would run
   `scrapy crawl book -a books=15,14`
2. If you would like to run it with emulated pubsub, you can
   run `scrapy crawl book -a books=15,14 -a project_id=test-project -a topic_name=test-topic`. You will also need to set
   the environmental variable `PUBSUB_EMULATOR_HOST=localhost:8681` (or whatever port your docker compose emulator is
   running on)