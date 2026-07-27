BOT_NAME = "job_crawler"
SPIDER_MODULES = ["job_crawler.spiders"]
NEWSPIDER_MODULE = "job_crawler.spiders"

# Politeness  d? xu?t ban d?u, CHUA có s? li?u th?t d? xác nh?n (crawler_design_final.md m?c 7)
ROBOTSTXT_OBEY = False  # t?t d? tránh 403 t? d?ch v? ch?ng bot (b?t l?i khi c?n thi?t)
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

EXTENSIONS = {
    "job_crawler.extensions.CrawlLogExtension": 500,
}

ITEM_PIPELINES = {
    "job_crawler.pipelines.JsonlRouterPipeline": 300,
}
