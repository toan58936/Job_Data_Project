"""Phase 1 — crawl trang listing ITviec, output jobs_meta_listing.jsonl.

[RÚT GỌN] Bỏ 6 field (work_mode_raw, salary_gated, posted_text, locations,
skills, salary_display) từng thêm ở bản trước — phát hiện chúng KHÔNG được
sources/itviec/parse.py._parse_listing() đọc lại, hàm đó tự trích y hệt dữ
liệu này lần thứ 2, độc lập, trực tiếp từ raw_html_listing đã lưu. 2 nơi cùng
làm 1 việc mà không liên quan tới nhau — rủi ro lệch kết quả nếu chỉ sửa 1 bên.
Quay lại đúng triết lý đã thống nhất: crawler chỉ "chụp ảnh" thô (title, url,
company_name, raw_html để audit nhanh), phần diễn giải (locations/skills/
work_mode/salary...) để "parse.py" đảm nhiệm 1 nơi duy nhất. Giờ khớp đúng 9
field cơ bản như topcv_listing_spider.py — 2 spider nhất quán schema.

[FIX] company_name: card thật có 2 thẻ <a href*="/companies/">, 1 cái là logo
(không có text), 1 cái mới chứa tên công ty (class text-rich-grey NGAY TRÊN
chính thẻ <a>, không phải phần tử con). Verify trên 20 card thật (itviec_list.html):
0/20 rỗng sau fix, so với 46/46 rỗng ở bản selector cũ dùng mô tả con sai.
Giữ lại fix này vì company_name vẫn là field core (khớp TopCV), không thuộc
nhóm bị bỏ ở trên.

[FIX v2] start_urls -> async def start(): request trang 1 trước đây được Scrapy
tự sinh qua cơ chế mặc định của start_urls, KHÔNG đi qua bất kỳ chỗ nào gắn
meta={"playwright": True} — chỉ trang 2 trở đi (tạo thủ công trong parse())
mới có. Override bằng async def start() — KHÔNG PHẢI def start_requests() kiểu
cũ (đã thử fix v1 dùng start_requests(), verify qua log thật: 0 request/0 item,
Scrapy 2.17's StartSpiderMiddleware không invoke được sync start_requests()) —
để trang 1 cũng nhất quán dùng Playwright, đúng với
SOURCE_REGISTRY["itviec"]["requires_browser"]=True. Đồng bộ pattern async def
start() đã chạy tốt ở itviec_detail_spider.py/topcv_detail_spider.py.
"""
import scrapy
import re
from job_crawler.spiders.base_spider import BaseSpider
from job_crawler.items import JobCrawlerItem


class ItviecListingSpider(BaseSpider):
    source_name = "itviec"
    name = "itviec_listing"

    base_url = "https://itviec.com/it-jobs/data-engineer"
    max_pages = 20

    async def start(self):
        yield scrapy.Request(
            url=f"{self.base_url}?page=1",
            callback=self.parse,
            meta={"playwright": True},
        )

    def parse(self, response):
        page_match = re.search(r'[?&]page=(\d+)', response.url)
        page_num = int(page_match.group(1)) if page_match else 1

        self.logger.info(f"🔥 Đang parse ITviec trang {page_num}")

        cards = response.css("div.job-card")
        if not cards:
            self.logger.info(f"Trang {page_num} không có card — dừng pagination.")
            return

        for card in cards:
            slug = card.attrib.get("data-search--job-selection-job-slug-value")
            if not slug:
                continue

            # Title & URL
            title_link = card.css('h3[data-search--job-selection-target="jobTitle"] a')
            title = title_link.css("::text").get(default="").strip()
            href = title_link.attrib.get("href", "")
            url_value = card.attrib.get("data-search--job-selection-job-url-value", "")
            url = href if href else url_value

            # Company name — lấy từ thẻ <a href*="/companies/"> có class
            # text-rich-grey NGAY TRÊN chính nó (compound selector, KHÔNG phải mô
            # tả con — card thật có 2 thẻ a href*="/companies/": 1 cái là logo
            # không text, 1 cái mới chứa tên công ty)
            company_name = ""
            company_nodes = card.css('a[href*="/companies/"].text-rich-grey')
            if not company_nodes:
                # fallback: lọc thủ công thẻ <a> nào thực sự có text (không phải logo rỗng)
                for a_node in card.css('a[href*="/companies/"]'):
                    text = a_node.xpath("string(.)").get(default="").strip()
                    if text:
                        company_nodes = a_node
                        break
            if company_nodes:
                company_name = company_nodes.xpath("string(.)").get(default="").strip()

            # Vị trí trên trang
            index_value = card.attrib.get("data-search--job-selection-job-index-value")

            # Tạo item — đúng 9 field cơ bản, khớp topcv_listing_spider.py.
            # raw_html vẫn lưu đầy đủ để parse.py tự trích locations/skills/
            # work_mode/salary khi cần, không phải tính lại ở đây.
            item = JobCrawlerItem()
            item["item_type"] = "listing"
            item["job_id"] = slug
            item["url"] = url
            item["title"] = title
            item["company_name"] = company_name
            item["raw_html"] = card.get()
            item["source"] = self.source_name
            item["batch_date"] = self.batch_date
            item["listing_page_num"] = page_num
            item["listing_position"] = int(index_value) if index_value is not None else None

            yield item

        # Pagination
        if page_num < self.max_pages:
            next_page = page_num + 1
            next_url = f"{self.base_url}?page={next_page}"
            yield scrapy.Request(
                url=next_url,
                callback=self.parse,
                meta={"playwright": True},
            )