"""
BaseSpider  d?c capability t? shared.source_registry.SOURCE_REGISTRY
(has_ajax_preview, requires_browser, id_strategy...) thay vì hard-code
trong t?ng spider con. M?i {source}_listing_spider.py / {source}_detail_spider.py
k? th?a t? dây.
"""
import scrapy
from shared.source_registry import SOURCE_REGISTRY


class BaseSpider(scrapy.Spider):
    source_name: str = ""  # override ? spider con, vd "itviec", "topcv"

    def __init__(self, batch_date: str = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not batch_date:
            raise ValueError("Thi?u -a batch_date=YYYY-MM-DD  không t? g?i datetime.now()")
        self.batch_date = batch_date
        self.registry_entry = SOURCE_REGISTRY[self.source_name]
