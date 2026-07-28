"""
BaseSpider  d?c capability t? shared.source_registry.SOURCE_REGISTRY
(has_ajax_preview, requires_browser, id_strategy...) thay vì hard-code
trong t?ng spider con. M?i {source}_listing_spider.py / {source}_detail_spider.py
k? th?a t? dây.
"""
import logging
import uuid
from datetime import datetime
from pathlib import Path

import scrapy
from scrapy import signals
from shared.source_registry import SOURCE_REGISTRY

logger = logging.getLogger(__name__)

CRAWL_LOG_FILE = Path(__file__).resolve().parent.parent.parent.parent / "data" / "metadata" / "crawl_log.jsonl"


class BaseSpider(scrapy.Spider):
    source_name: str = ""  # override ? spider con, vd "itviec", "topcv"

    def __init__(self, batch_date: str = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not batch_date:
            raise ValueError("Thi?u -a batch_date=YYYY-MM-DD  không t? g?i datetime.now()")
        self.batch_date = batch_date
        self.registry_entry = SOURCE_REGISTRY[self.source_name]

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider._on_spider_closed, signal=signals.spider_closed)
        return spider

    def _on_spider_closed(self, spider, **kwargs):
        try:
            stats = spider.crawler.stats.get_stats()
            jobs_found = stats.get("item_scraped_count", 0)
            http_error_codes = getattr(spider, "handle_httpstatus_list", [])
            jobs_failed = sum(
                stats.get(f"downloader/response_status_count/{code}", 0)
                for code in http_error_codes
            )

            run_id = str(uuid.uuid4())[:8]
            record = {
                "run_id": run_id,
                "source": getattr(spider, "source_name", spider.name),
                "spider_type": "listing" if "listing" in spider.name else "detail",
                "spider_name": spider.name,
                "batch_date": getattr(spider, "batch_date", None),
                "jobs_found": jobs_found,
                "jobs_failed": jobs_failed,
                "status": "success" if jobs_failed == 0 else "partial",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

            CRAWL_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CRAWL_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(__import__("json").dumps(record, ensure_ascii=False) + "\n")

            logger.info(f"[CrawlLog] Wrote crawl record: run_id={run_id}, jobs_found={jobs_found}, jobs_failed={jobs_failed}")
        except Exception as e:
            logger.exception(f"[CrawlLog] Failed: {e}")
