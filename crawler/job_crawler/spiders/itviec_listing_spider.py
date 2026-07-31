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

            # Company name — fix từ phiên bản trước
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
                meta={"playwright": True},
            )