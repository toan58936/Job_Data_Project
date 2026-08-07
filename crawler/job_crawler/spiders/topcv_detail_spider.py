"""Phase 2 — crawl detail TopCV, output jobs_meta_detail_status.jsonl.

Đọc file jobs_meta_listing.jsonl, lấy title và company_name từ đó,
và lưu vào item detail để file jobs_meta_detail_status.jsonl có đầy đủ metadata.

[SỬA] Đổi start_requests() (kiểu cũ, không được Scrapy 2.17 gọi trong project
này — xem giải thích chi tiết trong itviec_detail_spider.py) sang async def
start() (API mới từ Scrapy 2.13), giống itviec_detail_spider.py và
itviec_listing_spider.py.
"""
import json
import logging
from pathlib import Path

import scrapy
from job_crawler.spiders.base_spider import BaseSpider
from job_crawler.items import JobCrawlerItem

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class TopcvDetailSpider(BaseSpider):
    source_name = "topcv"
    name = "topcv_detail"

    custom_settings = {
        "DOWNLOAD_DELAY": 3,
        "CONCURRENT_REQUESTS": 2,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
    }

    async def start(self):
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
                title = row.get("title", "")
                company_name = row.get("company_name", "")
                if job_id and url and job_id not in crawled:
                    count += 1
                    yield scrapy.Request(
                        url=url,
                        callback=self.parse_detail,
                        errback=self.handle_request_failure,
                        meta={
                            "job_id": job_id,
                            "title": title,
                            "company_name": company_name,
                            "playwright": True,
                        },
                        dont_filter=True,
                    )
        logger.info(f"📋 Đã tạo {count} request detail cho TopCV")

    def parse_detail(self, response):
        job_id = response.meta.get("job_id", "unknown")
        title = response.meta.get("title", "")
        company_name = response.meta.get("company_name", "")
        html_content = response.text

        item = JobCrawlerItem()
        item["item_type"] = "detail"
        item["job_id"] = job_id
        item["url"] = response.url
        item["title"] = title
        item["company_name"] = company_name
        item["raw_html"] = html_content
        item["detail_crawled"] = True
        item["source"] = self.source_name
        item["batch_date"] = self.batch_date

        yield item