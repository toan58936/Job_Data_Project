from pipeline.model.source_normalized import SourceNormalized
from pipeline.model.job_posting import JobPosting
from pipeline.tools.skill_extractor import extract_skills
from shared.source_registry import SOURCE_REGISTRY
from datetime import datetime

def enrich(record: SourceNormalized) -> JobPosting:
    """
    Bước cuối của Pipeline: Làm giàu dữ liệu và Đóng gói.
    Chuyển đổi SourceNormalized -> JobPosting (Golden Schema).
    """
    registry_entry = SOURCE_REGISTRY.get(record.source, {})
    
    # 1. Trích xuất và chuẩn hoá kỹ năng
    extracted = extract_skills(record, registry_entry)
    
    # Lấy data_completeness từ bước validate (mặc định 'full' nếu lỡ sót)
    data_completeness = record.source_extra.get("data_completeness", "full")

    # 2. Map sang Schema Golden Record (JobPosting)
    return JobPosting(
        job_id=record.job_id,
        source=record.source,
        url=record.url,
        title=record.title,
        company_name=record.company_name,
        locations=record.locations,
        work_mode=record.work_mode,
        description_raw=record.description_raw,
        
        # Chưa có hàm phân loại seniority và domain, tạm để rỗng/None
        seniority_level=None,
        job_expertise=extracted.get("job_expertise", []),
        job_domains=extracted.get("job_domain", []),
        
        salary_status=record.salary_status,
        salary_min=record.salary_min,
        salary_max=record.salary_max,
        salary_currency="VND (Millions)",
        
        job_skills=extracted["skills_all"],  # Mảng kỹ năng phẳng cho Dashboard
        
        posted_date=record.source_extra.get("posted_date_parsed"),
        crawled_at=datetime.utcnow().isoformat(),
        
        listing_position=record.listing_position,
        data_completeness=data_completeness,
        source_extra={
            "skills_required": extracted["skills_required"],
            "skills_nice_to_have": extracted["skills_nice_to_have"],
            # Giữ lại các metadata gốc nếu cần
            "locations_raw": record.source_extra.get("locations_raw", []),
            "salary_raw": record.source_extra.get("salary_raw", "")
        }
    )