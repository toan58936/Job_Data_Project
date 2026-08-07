import scrapy
import re
from job_crawler.spiders.base_spider import BaseSpider
from job_crawler.items import JobCrawlerItem

DEFAULT_SEARCH_KEYWORD = "data-engineer"


def _slugify_keyword(keyword: str) -> str:
    """'Data Analyst' -> 'data-analyst' — ITviec dùng slug thường, gạch nối
    thay khoảng trắng trong URL /it-jobs/{slug}."""
    slug = keyword.strip().lower()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    return slug or DEFAULT_SEARCH_KEYWORD


class ItviecListingSpider(BaseSpider):
    source_name = "itviec"
    name = "itviec_listing"

    max_pages = 20

    def __init__(self, search_keyword: str = DEFAULT_SEARCH_KEYWORD, *args, **kwargs):
        # [FIX Vấn đề 3] base_url trước đây hard-code "data-engineer" ở cấp class
        # attribute -- muốn crawl từ khoá khác phải sửa code. Giờ nhận qua CLI:
        #   scrapy crawl itviec_listing -a batch_date=... -a search_keyword=data-analyst
        # BaseSpider.__init__ đã nhận **kwargs sẵn nên không cần sửa gì ở đó.
        super().__init__(*args, **kwargs)
        self.search_keyword = search_keyword
        self.base_url = f"https://itviec.com/it-jobs/{_slugify_keyword(search_keyword)}"

    async def start(self):
        yield scrapy.Request(
            url=f"{self.base_url}?page=1",
            callback=self.parse,
            meta={
                "playwright": True,
                # [FIX Vấn đề 4] Trước đây listing crawl KHÔNG đăng nhập trong khi
                # detail có đăng nhập -- 2 spider có thể thấy job set khác nhau nếu
                # ITviec cá nhân hoá kết quả theo tài khoản. Set thẳng context đã có
                # sẵn cookie (định nghĩa ở settings.py, KHÔNG phụ thuộc điều kiện
                # "spider.name == itviec_detail" trong LoginMiddleware -- context
                # Playwright dùng được bởi bất kỳ request nào tham chiếu đúng tên).
                # An toàn với trang public: có cookie login không ảnh hưởng gì nếu
                # trang không cần đăng nhập, chỉ là dùng dư context có sẵn.
                "playwright_context": "itviec_authed",
            },
        )

    def parse(self, response):
        page_match = re.search(r'[?&]page=(\d+)', response.url)
        page_num = int(page_match.group(1)) if page_match else 1

        self.logger.info(f"🔥 Đang parse ITviec trang {page_num} (keyword={self.search_keyword})")

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

            # Company name
            company_name = ""
            company_nodes = card.css('a[href*="/companies/"].text-rich-grey')
            if not company_nodes:
                for a_node in card.css('a[href*="/companies/"]'):
                    text = a_node.xpath("string(.)").get(default="").strip()
                    if text:
                        company_nodes = a_node
                        break
            if company_nodes:
                company_name = company_nodes.xpath("string(.)").get(default="").strip()

            # Vị trí trên trang
            index_value = card.attrib.get("data-search--job-selection-job-index-value")

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

        if page_num < self.max_pages:
            next_page = page_num + 1
            next_url = f"{self.base_url}?page={next_page}"
            yield scrapy.Request(
                url=next_url,
                callback=self.parse,
                meta={
                    "playwright": True,
                    "playwright_context": "itviec_authed",  # [FIX Vấn đề 4] — nhất quán với request đầu
                },
            )