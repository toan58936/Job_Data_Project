import scrapy

class JobCrawlerItem(scrapy.Item):
    # Bắt buộc cho mọi item
    item_type = scrapy.Field()          # "listing" hoặc "detail"
    job_id = scrapy.Field()
    source = scrapy.Field()
    batch_date = scrapy.Field()
    url = scrapy.Field()
    raw_html = scrapy.Field()           # HTML thô của card listing hoặc trang detail

    # Listing-specific
    title = scrapy.Field()              # Có thể được lấy từ listing
    company_name = scrapy.Field()
    listing_page_num = scrapy.Field()
    listing_position = scrapy.Field()

    # Detail-specific
    detail_crawled = scrapy.Field()     # True/False, thường là True khi crawl detail