"""
Phase 1 -- crawl trang listing ITviec, output jobs_meta_listing.jsonl qua pipelines.py.

Selector đã verify trực tiếp trên itviec_list.html (không đoán):
- Mỗi job card: div[data-job-key], attribute
  data-search--job-selection-job-slug-value chứa slug -> DÙNG LÀM job_id
  (KHÔNG dùng số cuối hay URL, vì ITviec dùng id_strategy=url_slug -- khác TopCV)
- Title: h3.text-break bên trong card
- URL detail PHẢI tự build /it-jobs/{slug} -- KHÔNG follow link AJAX preview
  có sẵn trong DOM (has_ajax_preview=True, xem crawler_design_final.md mục 4)
- Pagination: <link rel="next" href="...?page=N"> trong <head> -- tín hiệu chuẩn,
  đáng tin hơn TopCV (không có rel=next), follow tới khi thẻ này biến mất

requires_browser=True trong SOURCE_REGISTRY -- cần scrapy-playwright, thêm
meta={"playwright": True} khi bật middleware thật (chưa bật ở bản skeleton này,
xem crawler_design_final.md mục 7 -- việc bật Playwright để ở bước sau khi đã
verify selector đúng trên HTML tĩnh trước).
"""
import scrapy
from job_crawler.spiders.base_spider import BaseSpider
from job_crawler.items import JobItem


class ItviecListingSpider(BaseSpider):
    source_name = "itviec"
    name = "itviec_listing"

    start_urls = ["https://itviec.com/it-jobs/data-engineer"]

    def parse(self, response, page_num: int = 1):
        cards = response.css("div[data-job-key]")

        for card in cards:
            job_id = card.attrib.get("data-search--job-selection-job-slug-value")
            title = card.css("h3.text-break a::text").get() or card.css("h3.text-break::text").get()
            if not job_id or not title:
                self.logger.warning(f"Card thiếu slug hoặc title, bỏ qua: {card.get()[:200]}")
                continue

            item = JobItem()
            item["item_type"] = "listing"
            item["job_id"] = job_id
            item["url"] = f"https://itviec.com/it-jobs/{job_id}"  # build thẳng, KHÔNG dùng
                                                                    # link /content?job_index=N
            item["title"] = title.strip()
            item["raw_html"] = card.get()
            item["source"] = self.source_name
            item["batch_date"] = self.batch_date
            item["listing_page_num"] = page_num
            listing_index = card.attrib.get("data-search--job-selection-job-index-value")
            item["listing_position"] = int(listing_index) if listing_index is not None else None
            yield item

        next_page_url = response.css('link[rel="next"]::attr(href)').get()
        if next_page_url:
            yield response.follow(
                next_page_url,
                callback=self.parse,
                cb_kwargs={"page_num": page_num + 1},
            )