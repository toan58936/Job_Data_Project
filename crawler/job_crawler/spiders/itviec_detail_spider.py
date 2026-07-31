"""Spider for crawling ITviec job detail pages."""
import json
import logging
from pathlib import Path

import scrapy
from job_crawler.spiders.base_spider import BaseSpider
from job_crawler.items import JobCrawlerItem

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class ItviecDetailSpider(BaseSpider):
    source_name = "itviec"
    name = "itviec_detail"

    custom_settings = {
        "DOWNLOAD_DELAY": 5,
        "CONCURRENT_REQUESTS": 2,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
    }

    start_urls = ["https://itviec.com/it-jobs"]

    def parse(self, response):
        listing_path = PROJECT_ROOT / "data" / "raw" / self.source_name / self.batch_date / "jobs_meta_listing.jsonl"
        status_path = PROJECT_ROOT / "data" / "raw" / self.source_name / self.batch_date / "jobs_meta_detail_status.jsonl"

        if not listing_path.exists():
            logger.error(f"Không tìm thấy file listing: {listing_path}")
            return

        crawled = set()
        if status_path.exists():
            with open(status_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                        job_id = row.get("job_id")
                        if job_id:
                            crawled.add(job_id)
                    except json.JSONDecodeError:
                        continue

        count = 0
        with open(listing_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                job_id = row.get("job_id")
                url = row.get("url")
                if job_id and url and job_id not in crawled:
                    count += 1
                    yield scrapy.Request(
                        url=url,
                        callback=self.parse_detail,
                        meta={"job_id": job_id, "playwright": True},
                        dont_filter=True,
                    )
        logger.info(f"📋 Đã tạo {count} request detail cho ITviec")

    def parse_detail(self, response):
        job_id = response.meta.get("job_id", "unknown")
        html_content = response.text

        item = JobCrawlerItem()
        item["item_type"] = "detail"
        item["job_id"] = job_id
        item["url"] = response.url
        item["title"] = ""
        item["company_name"] = ""
        item["raw_html"] = html_content
        item["detail_crawled"] = True
        item["source"] = self.source_name
        item["batch_date"] = self.batch_date

        yield item