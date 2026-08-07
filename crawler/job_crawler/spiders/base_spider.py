"""BaseSpider – shared spider infrastructure for all sources.

Reads capability configuration from shared.source_registry.SOURCE_REGISTRY
(has_ajax_preview, requires_browser, id_strategy…) instead of hard-coding
per-source logic in each spider subclass.
"""
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
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

# [MỚI] Các mẫu lỗi đặc trưng cho việc crawl bị dừng giữa chừng (Ctrl+C/SIGINT,
# hoặc SIGTERM khi deploy) -- KHÔNG phản ánh site nguồn thật sự có vấn đề, chỉ
# là race condition giữa lệnh dừng và các page/context Playwright đang mở dở.
# Bằng chứng thật (batch 2026-08-06, run topcv_detail bị Ctrl+C giữa chừng):
# job_id=2168835 và job_id=2256232 cùng fail đúng 1 giây với dòng log SIGINT,
# lỗi "BrowserContext.new_page: Protocol error (Target.createTarget): Not
# supported" -- trong khi job_id=2200041 (TimeoutError, xảy ra TRƯỚC SIGINT
# gần 20 giây) là lỗi site thật (trang load quá 30s). Nếu không tách riêng,
# 1 script retry_failed.py đọc failed_jobs.jsonl sau này sẽ tính nhầm 2 job
# do người vận hành tự dừng thành "site đang chặn/lỗi", làm sai lệch quyết
# định backoff/alert.
_SHUTDOWN_ARTIFACT_PATTERNS = (
    "Protocol error",
    "Target page, context or browser has been closed",
    "Connection closed",
    "has been closed",
)


def _classify_failure_reason(error_message: str) -> str:
    """Phân loại lỗi request detail: "shutdown_interrupted" (do tự dừng crawl
    giữa chừng, không phải lỗi site) hay "site_error" (lỗi thật từ site nguồn:
    timeout, 403/429, connection refused...)."""
    for pattern in _SHUTDOWN_ARTIFACT_PATTERNS:
        if pattern in error_message:
            return "shutdown_interrupted"
    return "site_error"


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

    def handle_request_failure(self, failure):
        """[FIX Vấn đề 2 — P1, silent data loss]
        errback DÙNG CHUNG cho mọi request detail của mọi spider con (gán qua
        errback=self.handle_request_failure trong itviec_detail_spider.py /
        topcv_detail_spider.py). Trước đây KHÔNG có errback nào cả — request
        fail (403/429/timeout/connection refused...) sau khi hết RETRY_TIMES sẽ
        bị Scrapy âm thầm drop, job biến mất khỏi jobs_meta_detail_status.jsonl
        không dấu vết (evidence: batch 2026-07-31, 19/66 job ITviec "biến mất"
        không log, không alert — chính là lỗ hổng khiến _on_spider_closed() bên
        dưới từng luôn báo jobs_failed=0 sai, đã sửa riêng phần đếm ở đó, còn
        phần "biết job_id nào fail" thì cần method này).

        [SỬA] Thêm reason_category để phân biệt lỗi do site nguồn thật
        ("site_error") với lỗi phát sinh do crawl bị dừng giữa chừng
        ("shutdown_interrupted") -- xem _classify_failure_reason() ở trên.

        Ghi job_id + lý do fail ra data/raw/{source}/{batch_date}/failed_jobs.jsonl
        (append-only, cùng quy ước với jobs_meta_*.jsonl) — KHÔNG tự động retry ở
        đây, chỉ log để 1 script riêng (sau này, retry_failed.py) đọc và quyết định.
        """
        request = failure.request
        job_id = request.meta.get("job_id", "unknown")

        reason_type = failure.type.__name__ if failure.type else "UnknownError"
        status_code = None
        if hasattr(failure.value, "response") and failure.value.response is not None:
            status_code = failure.value.response.status

        error_message = str(failure.value)
        reason_category = _classify_failure_reason(error_message)

        record = {
            "job_id": job_id,
            "url": request.url,
            "reason_type": reason_type,
            "reason_category": reason_category,
            "status_code": status_code,
            "error_message": error_message[:300],
            "batch_date": getattr(self, "batch_date", None),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        failed_path = (
            _PROJECT_ROOT / "data" / "raw" / self.source_name / self.batch_date / "failed_jobs.jsonl"
        )
        failed_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(failed_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.error("[FailedJobs] Không ghi được failed_jobs.jsonl: %s", exc)

        logger.warning(
            "[FailedJobs] job_id=%s fail (%s/%s, status=%s): %s",
            job_id, reason_type, reason_category, status_code, error_message[:150],
        )

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
            # (xem topcv_detail_spider.py/itviec_detail_spider.py, gọi vào
            # self.handle_request_failure() ở trên — ghi chi tiết ra failed_jobs.jsonl).
            # Ở đây chỉ cần con số tổng hợp cấp-run để giám sát nhanh, không cần biết job_id nào.
            retry_http_codes = spider.crawler.settings.getlist("RETRY_HTTP_CODES", [])
            jobs_failed = sum(
                stats.get(f"downloader/response_status_count/{code}", 0)
                for code in retry_http_codes
            )
            # Cộng thêm lỗi không có response (timeout, connection refused, Playwright navigation
            # timeout...) — Scrapy tự động track dưới downloader/exception_count bất kể
            # handle_httpstatus_list. Đây là lớp lỗi mà đếm theo status code thuần không bắt được.
            # Lưu ý: con số này gộp CẢ site_error lẫn shutdown_interrupted (không tách theo
            # reason_category) -- đây chỉ là số tổng hợp cấp-run để giám sát nhanh; muốn biết
            # đúng tỉ lệ site_error thật, đọc failed_jobs.jsonl (đã có reason_category).
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
                # [FIX nhỏ, nhân tiện] datetime.utcnow() deprecated từ Python 3.12 —
                # đổi sang datetime.now(timezone.utc) để nhất quán với
                # handle_request_failure() ở trên, tránh DeprecationWarning rải
                # rác trong log (môi trường đang chạy Python 3.14.5).
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            CRAWL_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CRAWL_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

            logger.info(
                "[CrawlLog] Wrote crawl record: run_id=%s, jobs_found=%d, jobs_failed=%d",
                run_id,
                jobs_found,
                jobs_failed,
            )
        except Exception as e:
            logger.exception("[CrawlLog] Failed: %s", e)