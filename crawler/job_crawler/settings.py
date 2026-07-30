import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

BOT_NAME = "job_crawler"

SPIDER_MODULES = ["job_crawler.spiders"]
NEWSPIDER_MODULE = "job_crawler.spiders"

ROBOTSTXT_OBEY = False  # TODO: confirm intentional — both sites may block crawlers per robots.txt

DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {"headless": True}

DOWNLOAD_DELAY = 5
RANDOMIZE_DOWNLOAD_DELAY = True

CONCURRENT_REQUESTS = 2
CONCURRENT_REQUESTS_PER_DOMAIN = 2

COOKIES_ENABLED = False

DOWNLOADER_MIDDLEWARES = {
    "job_crawler.middlewares.LoginMiddleware": 543,
}

ITEM_PIPELINES = {
    "job_crawler.pipelines.JobCrawlerPipeline": 300,
}

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "raw")

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"

LOG_LEVEL = "INFO"

ITVIEC_EMAIL = os.getenv("ITVIEC_EMAIL")
ITVIEC_PASSWORD = os.getenv("ITVIEC_PASSWORD")