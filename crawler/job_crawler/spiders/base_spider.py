"""BaseSpider – shared spider infrastructure for all sources.

Reads capability configuration from shared.source_registry.SOURCE_REGISTRY
(has_ajax_preview, requires_browser, id_strategy…) instead of hard-coding
per-source logic in each spider subclass.
"""
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path

import scrapy
from scrapy import signals

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from shared.source_registry import SOURCE_REGISTRY

logger = logging.getLogger(__name__)

CRAWL_LOG_FILE = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data"
    / "metadata"
    / "crawl_log.jsonl"
)


class BaseSpider(scrapy.Spider):
    source_name: str = ""  # override in subclass, e.g. "itviec", "topcv"

    def __init__(self, batch_date: str = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not batch_date:
            raise ValueError(
                "Thiếu -a batch_date=YYYY-MM-DD; không tự sinh ngày hiện tại."
            )
        self.batch_date = batch_date
        self.registry_entry = SOURCE_REGISTRY[self.source_name]

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        batch_date = kwargs.pop(
            "batch_date", crawler.settings.get("BATCH_DATE", None)
        )
        spider = super().from_crawler(crawler, *args, batch_date=batch_date, **kwargs)
        crawler.signals.connect(spider._on_spider_closed, signal=signals.spider_closed)
        return spider

    def _on_spider_closed(self, spider, **kwargs):
        try:
            stats = spider.crawler.stats.get_stats()
            jobs_found = stats.get("item_scraped_count", 0)

            # [SỬA — bug xác nhận qua crawl_log.jsonl thật, batch 2026-07-31]
            # Bản cũ: http_error_codes = getattr(spider, "handle_httpstatus_list", [])
            # Không spider nào set attribute này (nó là khái niệm KHÁC: cho phép response lỗi
            # đi tới callback parse(), không phải "danh sách mã lỗi cần đếm") → luôn là [] →
            # jobs_failed LUÔN = 0 dù crawl fail thật. Bằng chứng: detail run batch 2026-07-31
            # báo "jobs_found: 47, jobs_failed: 0, status: success" trong khi listing cùng batch
            # tìm 66-68 job — gần 20 job biến mất không dấu vết.
            #
            # Sửa đúng: đếm theo RETRY_HTTP_CODES (cấu hình thật trong settings.py, khớp với mã
            # RetryMiddleware coi là lỗi cần retry) — CHÍNH mã đã hết lượt retry và bị
            # HttpErrorMiddleware chặn lại sẽ được các spider con báo qua errback riêng
            # (xem topcv_detail_spider.py/itviec_detail_spider.py: handle_detail_failure).
            # Ở đây chỉ cần con số tổng hợp cấp-run để giám sát nhanh, không cần biết job_id nào.
            retry_http_codes = spider.crawler.settings.getlist("RETRY_HTTP_CODES", [])
            jobs_failed = sum(
                stats.get(f"downloader/response_status_count/{code}", 0)
                for code in retry_http_codes
            )
            # Cộng thêm lỗi không có response (timeout, connection refused, Playwright navigation
            # timeout...) — Scrapy tự động track dưới downloader/exception_count bất kể
            # handle_httpstatus_list. Đây là lớp lỗi mà đếm theo status code thuần không bắt được.
            jobs_failed += stats.get("downloader/exception_count", 0)

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

            logger.info(
                "[CrawlLog] Wrote crawl record: run_id=%s, jobs_found=%d, jobs_failed=%d",
                run_id,
                jobs_found,
                jobs_failed,
            )
        except Exception as e:
            logger.exception("[CrawlLog] Failed: %s", e)