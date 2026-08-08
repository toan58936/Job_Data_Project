"""
JobPosting — Schema "Dữ liệu Vàng" (Golden Record) lưu trữ chính thức 
sau khi qua toàn bộ các bước làm sạch, chuẩn hóa và làm giàu (Enrich).
"""
from typing import Any, Optional
from pydantic import BaseModel, Field
from pipeline.model.source_normalized import SalaryStatus, WorkMode


class JobPosting(BaseModel):
    # === IDENTITY ===
    job_id: str                            # Định danh duy nhất (vd: itviec__2329)
    source: str                            # Nguồn gốc (itviec, topcv...)
    batch_date: str                        # Ngày batch crawl (YYYY-MM-DD)
    url: str                               # Đường dẫn chi tiết tuyển dụng

    # === JOB CORE ===
    title: str                             # Tiêu đề tin tuyển dụng
    company_name: str                      # Tên công ty
    locations: list[str] = Field(default_factory=list) # Danh sách địa điểm đã chuẩn hóa
    work_mode: Optional[WorkMode] = None   # Hình thức làm việc (onsite, hybrid, remote)
    description_raw: str                   # Mô tả công việc đã dọn sạch HTML

    # === CLASSIFICATION (enriched) ===
    seniority_level: Optional[str] = None  # Cấp độ (junior, middle, senior, lead...)
    job_role: Optional[str] = None         # Vai trò canonical (data_engineer, data_analyst, ...)

    # === SALARY (Đã chuẩn hóa về Triệu VNĐ) ===
    salary_status: SalaryStatus
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = "VND (Millions)"

    # === SKILLS (flat, normalized) ===
    job_skills: list[str] = Field(default_factory=list)    # Mảng kỹ năng phẳng (vd: python, spark, airflow)

    # === DATES ===
    posted_date: Optional[str] = None      # Ngày đăng tuyển (ISO format)
    crawled_at: Optional[str] = None       # Thời điểm hệ thống tiến hành crawl

    # === PIPELINE METADATA ===
    listing_position: Optional[int] = None # Vị trí hiển thị trên trang tìm kiếm
    data_completeness: str = "full"        # Trạng thái dữ liệu (full / listing_only)

    # === SOURCE-SPECIFIC ===
    source_extra: dict[str, Any] = Field(default_factory=dict) # Metadata đặc thù bổ sung