import scrapy

class JobCrawlerItem(scrapy.Item):
    item_type = scrapy.Field()
    job_id = scrapy.Field()
    source = scrapy.Field()
    batch_date = scrapy.Field()
    url = scrapy.Field()
    title = scrapy.Field()
    company_name = scrapy.Field()
    raw_html = scrapy.Field()
    raw_html_listing = scrapy.Field()
    raw_html_detail = scrapy.Field()
    detail_crawled = scrapy.Field()
    listing_page_num = scrapy.Field()
    listing_position = scrapy.Field()
    work_mode_raw = scrapy.Field()
    salary_gated = scrapy.Field()
    posted_text = scrapy.Field()

    # Thêm các trường mới
    locations = scrapy.Field()          # list hoặc string
    skills = scrapy.Field()             # list skill tags
    salary_display = scrapy.Field()     # text hiển thị trên card