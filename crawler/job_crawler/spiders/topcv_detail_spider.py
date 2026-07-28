"""
Spider detail cho TopCV.
- Đọc danh sách job_id/url từ data/raw/topcv/{batch_date}/jobs_meta_listing.jsonl
- Dùng Playwright (bắt buộc) để render Cloudflare challenge trên trang detail
- Output: item_type="detail" -> pipeline ghi raw_html và metadata riêng
"""
import json
from pathlib import Path

import scrapy
from job_crawler.items import JobItem
from job_crawler.pipelines import DATA_RAW_ROOT
from job_crawler.spiders.base_spider import BaseSpider


class TopcvDetailSpider(BaseSpider):
    source_name = "topcv"
    name = "topcv_detail"

    handle_httpstatus_list = [403, 429, 500, 502, 503]

    async def start(self):
        listing_path = DATA_RAW_ROOT / self.source_name / self.batch_date / "jobs_meta_listing.jsonl"
        self.logger.info(f"DEBUG start: listing_path={listing_path.resolve()}, exists={listing_path.exists()}")
        if not listing_path.exists():
            self.logger.error(
                f"Không tìm thấy file listing: {listing_path}. "
                f"Hãy chạy 'scrapy crawl topcv_listing -a batch_date={self.batch_date}' trước."
            )
            return

        count = 0
        with open(listing_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    job_id = record.get("job_id")
                    url = record.get("url")
                    if not job_id or not url:
                        self.logger.warning(f"Bỏ qua dòng thiếu job_id/url: {line[:100]}")
                        continue

                    count += 1
                    yield scrapy.Request(
                        url,
                        callback=self.parse,
                        meta={"job_id": job_id, "playwright": True},
                        dont_filter=True,
                    )
                except json.JSONDecodeError:
                    self.logger.warning(f"Bỏ qua dòng JSON không hợp lệ: {line[:100]}")
        self.logger.info(f"DEBUG start: yielded {count} requests")

    def parse(self, response):
        job_id = response.meta.get("job_id")
        if not job_id:
            self.logger.warning(f"Bỏ qua response thiếu job_id: {response.url}")
            return

        title = response.css("h1.box-header-job__title").xpath("string(.)").get(default="").strip()
        if not title:
            title = response.css("title::text").get(default="").strip()

        item = JobItem()
        item["item_type"] = "detail"
        item["job_id"] = job_id
        item["url"] = response.url
        item["title"] = title.strip() if title else ""
        item["raw_html"] = response.text
        item["source"] = self.source_name
        item["batch_date"] = self.batch_date

        yield item