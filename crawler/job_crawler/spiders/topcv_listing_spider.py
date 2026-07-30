"""Phase 1 — crawl listing TopCV, output jobs_meta_listing.jsonl.

Selector verify trực tiếp trên topcv_list.html:
- Mỗi job card: div.job-item-search-result, có attribute data-job-id, data-job-position
- Title + URL: h3.title > a (href chứa job_id ở số cuối trước .html)
- Company, location, salary, job type nằm trong các thẻ con của card

Pagination: ?page=N, dừng khi 1 trang trả về 0 card.
"""
from urllib.parse import parse_qs, urlparse, urlunparse, urlencode

import scrapy
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

    handle_httpstatus_list = [403, 429, 500, 502, 503]

    async def start(self):
        yield scrapy.Request(
            f"{self.base_url}?type_keyword=1&sba=1&page=1",
            callback=self.parse,
            meta={"page_num": 1, "playwright": True},
        )

    def parse(self, response):
        page_num = response.meta["page_num"]
        cards = response.css("div.job-item-search-result")

        if not cards:
            self.logger.info(
                "Trang %d không có card nào — dừng pagination.", page_num
            )
            return

        for card in cards:
            job_id = card.attrib.get("data-job-id")
            listing_position = card.attrib.get("data-job-position")
            title_link = card.css("h3.title a")
            if not job_id or not title_link:
                self.logger.warning(
                    "Card thiếu job_id hoặc title link, bỏ qua: %s",
                    card.get()[:200],
                )
                continue

            item = JobCrawlerItem()
            item["item_type"] = "listing"
            item["job_id"] = job_id
            item["url"] = _strip_tracking_params(title_link.attrib.get("href", ""))
            item["title"] = (
                title_link.css("span::text").get(default="").strip()
                or title_link.xpath("string(.)").get(default="").strip()
            )
            item["raw_html"] = card.get()
            item["source"] = self.source_name
            item["batch_date"] = self.batch_date
            item["listing_page_num"] = page_num
            item["listing_position"] = (
                int(listing_position) if listing_position else None
            )
            yield item

        if page_num < self.max_pages:
            next_page = page_num + 1
            yield scrapy.Request(
                f"{self.base_url}?type_keyword=1&sba=1&page={next_page}",
                callback=self.parse,
                meta={"page_num": next_page, "playwright": True},
            )