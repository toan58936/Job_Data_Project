"""
SourceNormalized -- output chuan cua sources/{source}/parse.py, input cho moi
pipeline_steps/ dung chung (shared_validate.py, cross_source_dedupe.py, shared_enrich.py...).

2 tang field (quyet dinh then chot cua toan bo thiet ke -- xem job_data_project_structure_v2.md
muc 3.3): CORE bat buoc moi nguon map duoc, EXTENSION (source_extra) cho field dac thu 1 nguon.
KHONG them field moi vao core tru khi >=2 nguon cung cung cap + co nhu cau dashboard that.
"""
from enum import Enum
from typing import Any, Optional
from datetime import date
from pydantic import BaseModel, Field


class SalaryStatus(str, Enum):
    DISCLOSED = "disclosed"
    NEGOTIABLE = "negotiable"
    AUTH_GATED = "auth_gated"
    NOT_PROVIDED = "not_provided"


class WorkMode(str, Enum):
    ONSITE = "onsite"
    HYBRID = "hybrid"
    REMOTE = "remote"


class SourceNormalized(BaseModel):
    job_id: str
    source: str
    batch_date: str
    url: str
    title: str
    company_name: str
    locations: list[str] = Field(default_factory=list)
    description_raw: str
    posted_date_raw: str
    posted_date: Optional[date] = None

    salary_status: SalaryStatus
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None

    work_mode: Optional[WorkMode] = None

    listing_position: Optional[int] = None

    source_extra: dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = False