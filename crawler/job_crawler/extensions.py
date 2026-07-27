import logging

logger = logging.getLogger(__name__)


class CrawlLogExtension:
    """Stub — ghi log đơn giản, TODO: ghi crawl_log.parquet."""

    def __init__(self):
        pass

    @classmethod
    def from_crawler(cls, crawler):
        ext = cls()
        crawler.signals.connect(ext.spider_closed, signal="spider_closed")
        return ext

    def spider_closed(self, spider):
        logger.info(
            f"[CrawlLog] Spider {spider.name} closed | "
            f"batch_date={getattr(spider, 'batch_date', 'N/A')}"
        )
