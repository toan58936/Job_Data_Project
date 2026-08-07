"""Spider for crawling ITviec job detail pages.

Đọc file jobs_meta_listing.jsonl, lấy title và company_name từ đó,
và lưu vào item detail để file jobs_meta_detail_status.jsonl có đầy đủ metadata.

[SỬA — trước] Bỏ start_urls, dùng start_requests() thay vì parse() đọc response
không dùng tới — tránh lãng phí 1 request khởi động.

[SỬA — mới] Thêm errback=self.handle_request_failure cho mỗi request detail.

[SỬA — quan trọng nhất, batch 2026-08-06] `def start_requests(self):` (kiểu cũ)
KHÔNG được Scrapy 2.17 gọi trong project này — xác nhận qua log thật: không có
bất kỳ dòng nào bên trong hàm được thực thi (không "Đã tạo X request", không cả
"Không tìm thấy file listing"), và cũng KHÔNG có ScrapyDeprecationWarning nhắc
tới start_requests (trong khi warning khác vẫn hiện bình thường) — nghĩa là
Scrapy coi spider này như KHÔNG override gì cả, rơi về hành vi mặc định (đọc
start_urls, mà start_urls không được định nghĩa -> rỗng -> 0 request, im lặng
hoàn toàn). itviec_listing_spider.py dùng `async def start()` (API mới, thêm từ
Scrapy 2.13) và chạy đúng — đổi theo đúng API đó, không dùng start_requests()
kiểu cũ nữa trong toàn bộ project này.
"""
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
        logger.info(f"📋 Đã tạo {count} request detail cho ITviec")

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