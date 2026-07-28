"""
Phase 1 — crawl trang listing TopCV, output jobs_meta_listing.jsonl qua pipelines.py.

Selector đã verify trực tiếp trên topcv_list.html (không đoán):
- Mỗi job card: div.job-item-search-result, có sẵn attribute data-job-id, data-job-position
- Title + URL: h3.title > a (href chứa job_id ở số cuối trước .html, kèm query string
  tracking ?ta_source=...&u_sr_id=... đổi mỗi lần crawl -> dùng data-job-id làm job_id,
  KHÔNG parse job_id từ URL)

CHƯA VERIFY: pagination. topcv_list.html mẫu không có <link rel="next"> hay link
phân trang nào trong DOM (khác ITviec) -> tạm dùng quy ước ?page=N phổ biến của TopCV,
dừng khi 1 trang trả về 0 card. Cần xác nhận đúng tham số này ở lần crawl thật đầu tiên
-- nếu sai tên param, spider sẽ dừng ngay ở trang 1 (an toàn, không loop vô hạn nhờ điều
kiện dừng dựa trên số card tìm được, không dựa trên đếm số trang cố định).
"""
import scrapy
from job_crawler.spiders.base_spider import BaseSpider
from job_crawler.items import JobItem


class TopcvListingSpider(BaseSpider):
    source_name = "topcv"
    name = "topcv_listing"

    base_url = "https://www.topcv.vn/tim-viec-lam-data-engineer"
    max_pages = 20  # an toàn, tránh loop vô hạn nếu logic dừng theo card-count bị lỗi

    # Cloudflare blocks plain scrapy requests (403) — use Playwright browser
    handle_httpstatus_list = [403, 429, 500, 502, 503]

    async def start(self):
        yield scrapy.Request(
            f"{self.base_url}?type_keyword=1&sba=1&page=1",
            callback=self.parse,
            meta={
                "page_num": 1,
                "playwright": True,
            },
        )

    def parse(self, response):
        page_num = response.meta["page_num"]
        cards = response.css("div.job-item-search-result")

        if not cards:
            self.logger.info(f"Trang {page_num} không có card nào -- dừng pagination.")
            return

        for card in cards:
            job_id = card.attrib.get("data-job-id")
            listing_position = card.attrib.get("data-job-position")
            title_link = card.css("h3.title a")
            if not job_id or not title_link:
                self.logger.warning(f"Card thiếu job_id hoặc title link, bỏ qua: {card.get()[:200]}")
                continue

            item = JobItem()
            item["item_type"] = "listing"
            item["job_id"] = job_id
            item["url"] = title_link.attrib.get("href")
            item["title"] = title_link.css("span::text").get(default="").strip() or title_link.xpath("string(.)").get(default="").strip()
            item["raw_html"] = card.get()
            item["source"] = self.source_name
            item["batch_date"] = self.batch_date
            item["listing_page_num"] = page_num
            item["listing_position"] = int(listing_position) if listing_position else None
            yield item

        if page_num < self.max_pages:
            next_page = page_num + 1
            yield scrapy.Request(
                f"{self.base_url}?type_keyword=1&sba=1&page={next_page}",
                callback=self.parse,
                meta={"page_num": next_page, "playwright": True},
            )
