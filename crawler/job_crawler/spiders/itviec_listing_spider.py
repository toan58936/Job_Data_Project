"""Phase 1 — crawl trang listing ITviec, output jobs_meta_listing.jsonl.

Selector đã verify trực tiếp trên ITviec listing page:
- Mỗi job card: div.job-card có data-search--job-selection-job-slug-value
- Title: h3 chứa a[data-search--job-selection-target="jobTitle"]
- URL: data-search--job-selection-job-url-value attribute hoặc href của a
- Company: span.text-rich-grey bên trong card
- Badges: "SUPER HOT", "Posted X ago"
- Work mode: "At office", "Hybrid", "Remote" trong card
- Salary gate: "Sign in to view salary" text

CHUAA VERIFY: pagination params cho ITviec listing — spider sẽ dừng
khi 1 trang trả về 0 card. Cần thử lần crawl đầu tiên để xác nhận
tham số page (ITviec dùng ?page=N hoặc khác).
"""
import scrapy
from job_crawler.spiders.base_spider import BaseSpider
from job_crawler.items import JobCrawlerItem


class ItviecListingSpider(BaseSpider):
    source_name = "itviec"
    name = "itviec_listing"

    base_url = "https://itviec.com/it-jobs/data-engineer"
    max_pages = 20

    handle_httpstatus_list = [403, 429, 500, 502, 503]

    async def start(self):
        yield scrapy.Request(
            f"{self.base_url}?page=1",
            callback=self.parse,
            meta={"page_num": 1, "playwright": True},
        )

    def parse(self, response):
        page_num = response.meta["page_num"]
        cards = response.css("div.job-card")

        if not cards:
            self.logger.info(
                f"Trang {page_num} không có card nào — dừng pagination."
            )
            return

        for card in cards:
            slug = card.attrib.get("data-search--job-selection-job-slug-value")
            url_value = card.attrib.get(
                "data-search--job-selection-job-url-value", ""
            )
            if not slug:
                continue

            job_id = slug
            title_link = card.css(
                'h3[data-search--job-selection-target="jobTitle"] a'
            )
            title = title_link.css("::text").get(default="").strip()
            href = title_link.attrib.get("href", "")
            url = href if href else url_value

            # company name
            company_nodes = card.css(
                'a[href*="/companies/"] span.text-rich-grey'
            )
            company_name = (
                company_nodes.xpath("string(.)").get(default="").strip()
                if company_nodes
                else ""
            )

            # work mode from inline text
            badge_text = " ".join(
                card.css("::text").getall()
            )
            work_mode = ""
            for wm in ("At office", "Hybrid", "Remote"):
                if wm in badge_text:
                    work_mode = wm
                    break

            # salary gated check
            salary_gated = "Sign in to view salary" in badge_text

            # posted date
            posted_text = ""
            for txt in card.css("::text").getall():
                t = txt.strip()
                if t.startswith("Posted"):
                    posted_text = t
                    break

            index_value = card.attrib.get(
                "data-search--job-selection-job-index-value"
            )
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
            item["listing_position"] = (
                int(index_value) if index_value is not None else None
            )
            item["work_mode_raw"] = work_mode
            item["salary_gated"] = salary_gated
            item["posted_text"] = posted_text
            yield item

        if page_num < self.max_pages:
            next_page = page_num + 1
            yield scrapy.Request(
                f"{self.base_url}?page={next_page}",
                callback=self.parse,
                meta={"page_num": next_page, "playwright": True},
            )