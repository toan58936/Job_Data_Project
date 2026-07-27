"""
Item — hộp chứa tối thiểu, KHÔNG type-check chặt.
RawRecord (pipeline/model/raw_record.py, giai đoạn sau) mới là nguồn sự thật.
"""
import scrapy


class JobItem(scrapy.Item):
    item_type = scrapy.Field()           # "listing" | "detail" — bắt buộc, dùng để route trong pipelines.py
    job_id = scrapy.Field()              # bắt buộc — join key, KHÔNG dùng url
    url = scrapy.Field()                 # giữ để debug/audit
    title = scrapy.Field()
    raw_html = scrapy.Field()
    source = scrapy.Field()
    batch_date = scrapy.Field()
    listing_page_num = scrapy.Field()    # chỉ có ở listing item
    listing_position = scrapy.Field()    # chỉ có ở listing item