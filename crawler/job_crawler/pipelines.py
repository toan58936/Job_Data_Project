import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from itemadapter import ItemAdapter
from shared.utils import safe_id

DATA_RAW_ROOT = (
    Path(__file__).resolve().parent.parent.parent / "data" / "raw"
)

FILENAME_BY_TYPE = {
    "listing": "jobs_meta_listing.jsonl",
    "detail": "jobs_meta_detail_status.jsonl",
}
RAW_HTML_SUBDIR_BY_TYPE = {
    "listing": "listing",
    "detail": "job_detail",
}


class JobCrawlerPipeline:
    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        pipeline._crawler = crawler
        return pipeline

    @property
    def _spider(self):
        return self._crawler.spider

    def open_spider(self, spider=None):
        if spider is None:
            spider = self._spider
        self.seen_job_ids = {"listing": set(), "detail": set()}
        for item_type, filename in FILENAME_BY_TYPE.items():
            path = self._jsonl_path(spider, filename)
            if not path.exists():
                continue
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                        self.seen_job_ids[item_type].add(row["job_id"])
                    except (json.JSONDecodeError, KeyError):
                        spider.logger.warning(
                            "Dòng JSONL hỏng trong %s, bỏ qua khi preload: %s",
                            path,
                            line[:100],
                        )
        spider.logger.info(
            "[Pipeline] Preloaded seen_job_ids: listing=%d, detail=%d",
            len(self.seen_job_ids["listing"]),
            len(self.seen_job_ids["detail"]),
        )

    def _batch_dir(self, spider) -> Path:
        d = DATA_RAW_ROOT / spider.source_name / spider.batch_date
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _jsonl_path(self, spider, filename: str) -> Path:
        return self._batch_dir(spider) / filename

    def _raw_html_path(self, spider, item_type: str, job_id: str) -> Path:
        subdir = RAW_HTML_SUBDIR_BY_TYPE[item_type]
        d = self._batch_dir(spider) / "raw_html" / subdir
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{safe_id(job_id)}.html"

    def process_item(self, item, spider=None):
        if spider is None:
            spider = self._spider
        adapter = ItemAdapter(item)
        item_type = adapter.get("item_type")
        job_id = adapter.get("job_id")

        if item_type not in FILENAME_BY_TYPE:
            spider.logger.warning(
                "item_type không hợp lệ (%r), bỏ qua item job_id=%s",
                item_type,
                job_id,
            )
            return item
        if not job_id:
            spider.logger.warning(
                "Item thiếu job_id (%s), bỏ qua: %s",
                item_type,
                adapter.get("url"),
            )
            return item
        if job_id in self.seen_job_ids[item_type]:
            spider.logger.debug(
                "job_id=%s đã có trong %s, skip (idempotent rerun).",
                job_id,
                item_type,
            )
            return item

        raw_html = adapter.get("raw_html", "") or ""
        self._raw_html_path(spider, item_type, job_id).write_text(
            raw_html, encoding="utf-8"
        )

        meta = {k: v for k, v in adapter.asdict().items() if k != "raw_html"}
        with open(
            self._jsonl_path(spider, FILENAME_BY_TYPE[item_type]),
            "a",
            encoding="utf-8",
        ) as f:
            f.write(json.dumps(meta, ensure_ascii=False) + "\n")

        self.seen_job_ids[item_type].add(job_id)
        return item