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

    # 1. Trích xuất và chuẩn hoá kỹ năng (Bây giờ trả về 1 FLAT LIST duy nhất)
    extracted_skills = extract_skills(record, registry_entry)

    # [SỬA] job_expertise/job_domains trước đây lấy từ extracted.get("job_expertise", [])/
    # extracted.get("job_domain", []) -- nhưng extract_skills() CHỈ trả về kỹ năng. Kết quả: 
    # MỌI JobPosting đều có job_expertise=[]/job_domains=[] dù dữ liệu thô có thật 100%
    # (đã verify trên itviec_normalized.jsonl: 45/45 job có job_expertise_raw/
    # job_domain_raw không rỗng). Đây là 2 field pass-through thuần tuý từ itviec
    # (topcv không có khái niệm tương đương), không cần canonical hoá qua taxonomy
    # skill nên đọc thẳng từ source_extra, không đi qua extract_skills().
    job_expertise = record.source_extra.get("job_expertise_raw", [])
    job_domains = record.source_extra.get("job_domain_raw", [])

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

        # Chưa có hàm phân loại seniority, tạm để rỗng/None
        seniority_level=None,
        job_expertise=job_expertise,
        job_domains=job_domains,

        salary_status=record.salary_status,
        salary_min=record.salary_min,
        salary_max=record.salary_max,
        salary_currency="VND (Millions)",

        # Map trực tiếp mảng phẳng vào trường job_skills
        job_skills=extracted_skills,

        posted_date=record.source_extra.get("posted_date_parsed"),
        crawled_at=datetime.utcnow().isoformat(),

        listing_position=record.listing_position,
        data_completeness=data_completeness,
        
        # source_extra giờ đây đã hoàn toàn sạch sẽ, không lưu rác phái sinh
        source_extra={
            "locations_raw": record.source_extra.get("locations_raw", []),
            "salary_raw": record.source_extra.get("salary_raw", ""),
        },
    )