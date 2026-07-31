from pipeline.model.source_normalized import SourceNormalized
from pipeline.tools.skill_extractor import extract_skills
from shared.source_registry import SOURCE_REGISTRY


def enrich(record: SourceNormalized) -> SourceNormalized:
    """
    Làm giàu (enrich) bản ghi đã được parse thô.
    Bước này thực hiện chuẩn hoá kỹ năng, loại bỏ kỹ năng rác và tạo ra mảng `skills_all`.
    """
    registry_entry = SOURCE_REGISTRY.get(record.source, {})
    
    # 1. Trích xuất và chuẩn hoá kỹ năng
    extracted = extract_skills(record, registry_entry)
    
    # Ghi nhận kết quả chuẩn hoá vào bản ghi
    record.source_extra["skills_all"] = extracted["skills_all"]
    record.source_extra["skills_required"] = extracted["skills_required"]
    record.source_extra["skills_nice_to_have"] = extracted["skills_nice_to_have"]
    
    # Có thể làm thêm các bước làm giàu khác (vd: title classification, salary conversion)
    
    return record
