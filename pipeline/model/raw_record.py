"""
RawRecord — nguồn sự thật (Pydantic, có validate) cho dữ liệu thô sau khi merge.
Khác với crawler/job_crawler/items.py (hộp chứa tối thiểu, không type-check),
RawRecord là nơi ép kiểu và validate trước khi đưa vào sources/{source}/parse.py.

Field đặt tên khớp trực tiếp với jobs_meta_listing.jsonl / jobs_meta_detail_status.jsonl
thật (đã verify trên dữ liệu TopCV/ITviec crawl thật) — không suy đoán.
"""
from typing import Optional
from pydantic import BaseModel


class RawRecord(BaseModel):
    # --- luôn có, tới từ jobs_meta_listing.jsonl (Phase 1) ---
    job_id: str
    source: str
    batch_date: str
    url: str                                   # URL detail — có thể kèm query tracking (TopCV),
                                                # giữ nguyên để audit, KHÔNG dùng để join (đã chốt)
    title_listing: str                         # title lấy từ trang listing (đã sửa bug nested-tag)
    listing_page_num: Optional[int] = None
    listing_position: Optional[int] = None
    raw_html_listing: Optional[str] = None      # HTML card thô từ trang listing

    # --- chỉ có nếu Phase 2 (detail) đã crawl xong ---
    detail_crawled: bool = False
    title_detail: Optional[str] = None          # title lấy từ trang detail (có thể khác listing,
                                                # ví dụ TopCV detail dính "Tuyển ... làm việc tại ...")
    raw_html_detail: Optional[str] = None        # HTML đầy đủ trang detail — input chính cho parse.py

    class Config:
        frozen = True  # RawRecord là dữ liệu đã merge xong, không nên sửa sau khi tạo
