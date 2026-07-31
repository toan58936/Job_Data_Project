"""Phase 1 — crawl trang listing ITviec, output jobs_meta_listing.jsonl.
Cải tiến: lấy company_name, locations, skills, salary_display chính xác.
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

    start_urls = [f"{base_url}?page=1"]

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

            # Company name – lấy từ link text hoặc span bên trong
            company_name = ""
            company_selector = 'a[href*="/companies/"] .text-rich-grey'
            company_nodes = card.css(company_selector)
            if not company_nodes:
                # fallback: lấy trực tiếp từ thẻ a
                company_nodes = card.css('a[href*="/companies/"]')
            if company_nodes:
                company_name = company_nodes.xpath("string(.)").get(default="").strip()

            # Work mode & salary gated từ text
            badge_text = " ".join(card.css("::text").getall())
            work_mode = ""
            for wm in ("At office", "Hybrid", "Remote"):
                if wm in badge_text:
                    work_mode = wm
                    break

            salary_gated = "Sign in to view salary" in badge_text

            # Posted date
            posted_text = ""
            posted_node = card.css("span.small-text.text-dark-grey")
            if posted_node:
                posted_text = posted_node.xpath("string(.)").get(default="").strip()

            # Vị trí trên trang
            index_value = card.attrib.get("data-search--job-selection-job-index-value")

            # ** Lấy locations **
            locations = []
            location_node = card.css('div.imt-1.d-flex.align-items-center svg.feather-icon-map-pin + div.text-rich-grey')
            if location_node:
                loc_text = location_node.xpath("string(.)").get(default="").strip()
                if loc_text:
                    locations = [loc.strip() for loc in loc_text.split("-") if loc.strip()]
            # fallback: tìm bất kỳ div nào có text chứa dấu "-" và map-pin gần đó
            if not locations:
                loc_divs = card.css('div.imt-1.d-flex.align-items-center')
                for div in loc_divs:
                    if div.css('svg.feather-icon-map-pin'):
                        text = div.xpath("string(.)").get(default="").strip()
                        if text and any(city in text for city in ["Ha Noi", "Ho Chi Minh", "Da Nang"]):
                            locations = [loc.strip() for loc in text.split("-") if loc.strip()]
                            break

            # ** Lấy skills **
            skills = []
            skill_tags = card.css('a.itag.itag-light.itag-sm')
            for tag in skill_tags:
                skill_text = tag.xpath("string(.)").get(default="").strip()
                if skill_text:
                    skills.append(skill_text)

            # ** Lấy salary display **
            salary_display = ""
            salary_node = card.css('div.salary a.sign-in-view-salary')
            if salary_node:
                salary_text = salary_node.xpath("string(.)").get(default="").strip()
                salary_display = salary_text if salary_text else "Sign in to view salary"
            else:
                # Có thể có trường hợp hiển thị số tiền
                salary_node2 = card.css('div.salary span')
                if salary_node2:
                    salary_display = salary_node2.xpath("string(.)").get(default="").strip()

            # Tạo item
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
            item["work_mode_raw"] = work_mode
            item["salary_gated"] = salary_gated
            item["posted_text"] = posted_text

            # Các trường mới
            item["locations"] = locations
            item["skills"] = skills
            item["salary_display"] = salary_display

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