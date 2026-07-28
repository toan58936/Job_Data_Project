import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BOT_NAME = "job_crawler"
SPIDER_MODULES = ["job_crawler.spiders"]
NEWSPIDER_MODULE = "job_crawler.spiders"

# Politeness  d? xu?t ban d?u, CHUA có s? li?u th?t d? xác nh?n (crawler_design_final.md m?c 7)
ROBOTSTXT_OBEY = True
AUTOTHROTTLE_ENABLED = True
CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 2  # tuning riêng theo ngu?n ? spider con n?u c?n (ITviec 3-5s do Playwright)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

# Playwright settings for Cloudflare bypass (TopCV)
PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
}

DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

ITEM_PIPELINES = {
    "job_crawler.pipelines.JsonlRouterPipeline": 300,
}
