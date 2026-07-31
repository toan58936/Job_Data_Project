"""Phase 1 — crawl listing TopCV, output jobs_meta_listing.jsonl.
Chỉ thu thập raw HTML và metadata cơ bản.
"""
from urllib.parse import parse_qs, urlparse, urlunparse, urlencode
import scrapy
import re
from job_crawler.spiders.base_spider import BaseSpider
from job_crawler.items import JobCrawlerItem

TRACKING_PARAMS = {"ta_source", "u_sr_id"}

def _strip_tracking_params(url: str) -> str:
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    clean_params = {k: v for k, v in params.items() if k not in TRACKING_PARAMS}
    return urlunparse(parsed._replace(query=urlencode(clean_params, doseq=True), fragment=""))


class TopcvListingSpider(BaseSpider):
    source_name = "topcv"
    name = "topcv_listing"

    base_url = "https://www.topcv.vn/tim-viec-lam-data-engineer"
    max_pages = 20

    start_urls = [f"{base_url}?type_keyword=1&sba=1&page=1"]

    def parse(self, response):
        page_match = re.search(r'[?&]page=(\d+)', response.url)
        page_num = int(page_match.group(1)) if page_match else 1

        self.logger.info(f"🔥 Đang parse TopCV trang {page_num}")

        cards = response.css("div.job-item-search-result")
        if not cards:
            self.logger.info(f"Trang {page_num} không có card — dừng pagination.")
            return

        for card in cards:
            job_id = card.attrib.get("data-job-id")
            listing_position = card.attrib.get("data-job-position")
            if not job_id:
                self.logger.warning("Card thiếu data-job-id, bỏ qua: %s", card.get()[:200])
                continue

            title_link = card.css("h3.title a")
            if not title_link:
                self.logger.warning("Card thiếu title link, bỏ qua: %s", card.get()[:200])
                continue

            title = (
                title_link.css("span::text").get(default="").strip()
                or title_link.xpath("string(.)").get(default="").strip()
            )
            url = _strip_tracking_params(title_link.attrib.get("href", ""))

            company_name = ""
            company_node = card.css("a.company span.company-name")
            if company_node:
                company_name = company_node.xpath("string(.)").get(default="").strip()

            item = JobCrawlerItem()
            item["item_type"] = "listing"
            item["job_id"] = job_id
            item["url"] = url
            item["title"] = title
            item["company_name"] = company_name
            item["raw_html"] = card.get()
            item["source"] = self.source_name
            item["batch_date"] = self.batch_date
            item["listing_page_num"] = page_num
            item["listing_position"] = int(listing_position) if listing_position else None

            yield item

        if page_num < self.max_pages:
            next_page = page_num + 1
            next_url = f"{self.base_url}?type_keyword=1&sba=1&page={next_page}"
            yield scrapy.Request(
                url=next_url,
                callback=self.parse,
                meta={"page_num": next_page},
            )