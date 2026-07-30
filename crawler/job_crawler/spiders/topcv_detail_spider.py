"""Phase 2 — crawl detail TopCV, output jobs_meta_detail_status.jsonl.

Reads listing JSONL from Phase 1, visits each job URL, saves raw HTML.
Uses Playwright (Cloudflare protection on TopCV).
"""
import json
import sys
from pathlib import Path

import scrapy

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from job_crawler.items import JobCrawlerItem
from job_crawler.spiders.base_spider import BaseSpider
from shared.utils import safe_id

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class TopcvDetailSpider(BaseSpider):
    source_name = "topcv"
    name = "topcv_detail"

    custom_settings = {
        "DOWNLOAD_DELAY": 3,
        "CONCURRENT_REQUESTS": 2,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
    }

    def start_requests(self):
        listing_path = (
            PROJECT_ROOT
            / "data"
            / "raw"
            / self.source_name
            / self.batch_date
            / "jobs_meta_listing.jsonl"
        )
        status_path = (
            PROJECT_ROOT
            / "data"
            / "raw"
            / self.source_name
            / self.batch_date
            / "jobs_meta_detail_status.jsonl"
        )

        crawled = set()
        if status_path.exists():
            with open(status_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                        crawled.add(row.get("job_id"))
                    except json.JSONDecodeError:
                        continue

        pending = []
        if listing_path.exists():
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
                        pending.append((job_id, url))

        self.logger.info(
            "Loaded %d detail URLs (%d already crawled) for batch %s",
            len(pending),
            len(crawled),
            self.batch_date,
        )

        for job_id, url in pending:
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
                meta={"job_id": job_id, "playwright": True},
                dont_filter=True,
            )

    def parse_detail(self, response):
        job_id = response.meta.get("job_id", "unknown")
        slug = safe_id(job_id) + ".html"
        raw_html_dir = (
            PROJECT_ROOT
            / "data"
            / "raw"
            / self.source_name
            / self.batch_date
            / "raw_html"
            / "job_detail"
        )
        raw_html_dir.mkdir(parents=True, exist_ok=True)
        out_path = raw_html_dir / slug

        html_content = response.text
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        self.logger.info(
            "Saved detail HTML for %s (%d bytes)", job_id, len(html_content)
        )

        item = JobCrawlerItem()
        item["item_type"] = "detail"
        item["job_id"] = job_id
        item["url"] = response.url
        item["title"] = ""
        item["company_name"] = ""
        item["raw_html_detail"] = html_content
        item["detail_crawled"] = True
        item["source"] = self.source_name
        item["batch_date"] = self.batch_date
        yield item