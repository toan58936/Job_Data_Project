"""Spider for crawling ITviec job detail pages.

Reads the listing JSONL produced by itviec_listing spider,
then visits each job URL and saves the raw HTML via the pipeline.

The LoginMiddleware automatically attaches session cookies
so that salary data is visible for logged-in users.
"""
import json
import logging
from pathlib import Path

import scrapy

from job_crawler.items import JobCrawlerItem
from job_crawler.spiders.base_spider import BaseSpider

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

    def start_requests(self):
        self._load_urls()
        for job_id, url in self._urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse_detail,
                meta={"job_id": job_id},
                dont_filter=True,
            )

    def _load_urls(self):
        self._urls = []
        status_path = (
            PROJECT_ROOT
            / "data"
            / "raw"
            / self.source_name
            / self.batch_date
            / "jobs_meta_detail_status.jsonl"
        )
        listing_path = (
            PROJECT_ROOT
            / "data"
            / "raw"
            / self.source_name
            / self.batch_date
            / "jobs_meta_listing.jsonl"
        )

        existing = set()
        if status_path.exists():
            with open(status_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        existing.add(rec.get("job_id"))
                    except json.JSONDecodeError:
                        continue

        if listing_path.exists():
            with open(listing_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    job_id = rec.get("job_id")
                    url = rec.get("url")
                    if job_id and url and job_id not in existing:
                        self._urls.append((job_id, url))

        logger.info(
            "Loaded %d detail URLs for batch %s",
            len(self._urls),
            self.batch_date,
        )

    def parse_detail(self, response):
        job_id = response.meta.get("job_id", "unknown")
        slug = job_id.replace("/", "-") + ".html"
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

        logger.info("Saved detail HTML for %s (%d bytes)", job_id, len(html_content))

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