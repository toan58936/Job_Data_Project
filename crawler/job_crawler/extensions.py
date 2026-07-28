import json
import uuid
from pathlib import Path
from datetime import datetime

DATA_ROOT = Path(__file__).resolve().parent.parent.parent / "data"
METADATA_DIR = DATA_ROOT / "metadata"
CRAWL_LOG_FILE = METADATA_DIR / "crawl_log.jsonl"


class CrawlLogExtension:
    def __init__(self):
        METADATA_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_crawler(cls, crawler):
        ext = cls()
        try:
            crawler.signals.connect(ext.spider_closed, signal="spider_closed")
        except Exception as e:
            import sys
            sys.stderr.write(f"[CrawlLogExtension] connect FAILED: {e}\n")
        return ext

    def spider_closed(self, spider, **kwargs):
        spider.logger.info("[CrawlLogExtension] spider_closed CALLED")
        try:
            stats = spider.crawler.stats.get_stats()
            jobs_found = stats.get("item_scraped_count", 0)
            jobs_failed = stats.get("spider_exceptions/Exception", 0)

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
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

            spider.logger.info(f"[CrawlLog] Wrote crawl record: run_id={run_id}, jobs_found={jobs_found}, jobs_failed={jobs_failed}")
        except Exception as e:
            spider.logger.exception(f"[CrawlLog] Failed: {e}")
