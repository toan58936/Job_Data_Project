from typing import Any, Optional

from pipeline.config.skills_taxonomy import SKILLS_TAXONOMY
from pipeline.tools.vocab_gap_logger import log_unrecognized_skill


def _build_alias_lower_map() -> dict[str, str]:
    alias_map: dict[str, str] = {}
    for entry in SKILLS_TAXONOMY.values():
        canonical = entry["canonical"]
        for alias in entry["aliases"]:
            alias_map[alias.lower()] = canonical
    return alias_map


def _build_case_sensitive_alias_set() -> set[str]:
    """[SỬA] Trước đây filter case-sensitive áp theo ĐỘ DÀI chuỗi match (len(span)==2),
    vô tình bắt luôn alias "ML" (machine-learning) dù alias đó chưa từng cần case-sensitive
    -- đã verify: 4/10 job topcv, 4/7 job itviec nhắc riêng lẻ "ML" bị mất hẳn Machine
    Learning. Giờ khai báo tường minh CHỈ alias "AI" cần case đúng (do va chạm đại từ tiếng
    Việt "ai"), lấy từ 1 set cấu hình rõ ràng thay vì suy luận qua độ dài."""
    return {"AI"}


_ALIAS_LOWER_MAP = _build_alias_lower_map()
_CASE_SENSITIVE_ALIASES = _build_case_sensitive_alias_set()

_KEYWORD_PROCESSOR = None
_NOISE_SKILLS = {
    "English",
    "Team Management",
    "Fresher Accepted",
    "Project Management",
    "Stakeholder management",
    "Communication",
    "Leadership",
    "Soft Skills",
    "Analytical Skills",
}


def _get_keyword_processor():
    global _KEYWORD_PROCESSOR
    if _KEYWORD_PROCESSOR is None:
        from flashtext import KeywordProcessor

        kp = KeywordProcessor(case_sensitive=False)
        for entry in SKILLS_TAXONOMY.values():
            for alias in entry["aliases"]:
                kp.add_keyword(alias, entry["canonical"])
        _KEYWORD_PROCESSOR = kp
    return _KEYWORD_PROCESSOR


def canonicalize_skill(skill: str, source: str, job_id: str) -> str:
    """[SỬA] Không còn trả None/xoá candidate không khớp taxonomy. Khớp -> trả canonical.
    Không khớp -> log vào vocab_gap_logger (để phát hiện taxonomy thiếu) NHƯNG VẪN trả lại
    chuỗi gốc đã strip, để downstream không mất tín hiệu. Trước đây trả None khiến job có
    tag hợp lệ nhưng không khớp taxonomy (vd job "Kỹ Sư Giải Cứu Dữ Liệu", 28 tag) bị mất
    trắng skills_all -- không phân biệt được "job không có skill" với "job có skill nhưng
    taxonomy chưa nhận diện"."""
    stripped = skill.strip()
    lowered = stripped.lower()
    if lowered in _ALIAS_LOWER_MAP:
        return _ALIAS_LOWER_MAP[lowered]

    log_unrecognized_skill(skill, source, job_id)
    return stripped


def canonicalize_skills_list(skills: list[str], source: str, job_id: str) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for s in skills:
        c = canonicalize_skill(s, source, job_id)
        if c and c not in seen:
            seen.add(c)
            result.append(c)
    return result


def _extract_skills_from_tags(record: Any, structure: Optional[str]) -> list[str]:
    """Đọc skill từ tag có cấu trúc trong source_extra (nếu nguồn có hỗ trợ và
    bản ghi này thực sự có điền tag). 
    [SỬA] Trả về 1 flat list duy nhất thay vì dict."""
    source = record.source
    job_id = record.job_id
    raw_skills = []

    if structure == "flat":
        raw_skills = record.source_extra.get("skills_raw", [])
    elif structure == "grouped":
        req = record.source_extra.get("skills_required_raw", [])
        nice = record.source_extra.get("skills_nice_to_have_raw", [])
        raw_skills = req + nice

    return canonicalize_skills_list(raw_skills, source, job_id)


def _extract_skills_from_text(record: Any) -> list[str]:
    """Fallback: dò từ khoá kỹ năng (flashtext, theo SKILLS_TAXONOMY) trực tiếp
    trong description_raw + requirements_raw (nếu nguồn có field này trong
    source_extra — TopCV có, không phải nguồn nào cũng có nên dùng .get()).

    [SỬA] KHÔNG còn áp _NOISE_SKILLS ở đây -- lọc noise giờ chỉ làm 1 lần duy nhất
    ở extract_skills() sau khi đã union tag+text, để áp dụng nhất quán cho CẢ 2
    nhánh thay vì chỉ lọc riêng nhánh text (bug cũ: 12/46 job itviec lọt noise qua
    nhánh tag vì _NOISE_SKILLS không hề chạm tới _extract_skills_from_tags)."""
    kp = _get_keyword_processor()

    text_parts = [record.description_raw or ""]
    requirements_raw = record.source_extra.get("requirements_raw", "")
    if requirements_raw:
        text_parts.append(requirements_raw)
    text = " ".join(text_parts)

    if not text.strip():
        return []

    matches = kp.extract_keywords(text, span_info=True)
    filtered: list[str] = []
    for canonical, start, end in matches:
        span = text[start:end]
        # [SỬA] Chỉ áp điều kiện case khi span khớp (không phân biệt hoa/thường) với 1
        # alias đã khai báo trong _CASE_SENSITIVE_ALIASES (hiện chỉ có "AI") -- lúc đó
        # bắt buộc span phải TRÙNG NGUYÊN VĂN alias mới được chấp nhận (span="Ai"/"ai"
        # bị loại, span="AI" thì giữ). Match của canonical khác (vd "ML", "Kafka") không
        # đi qua nhánh này nên không còn bị bắt nhầm như bản trước.
        if span.lower() in {a.lower() for a in _CASE_SENSITIVE_ALIASES} and span not in _CASE_SENSITIVE_ALIASES:
            continue
        filtered.append(canonical)

    return list(dict.fromkeys(filtered))


def extract_skills(record: Any, registry_entry: dict) -> list[str]:
    """Trích skill cho 1 bản ghi SourceNormalized.

    Luôn chạy cả nhánh tag và text, rồi union lại. 
    [SỬA] Trả về một mảng phẳng (flat list) duy nhất, loại bỏ sự rườm rà của dict 3 key.
    [SỬA] _NOISE_SKILLS áp dụng 1 LẦN DUY NHẤT ở đây, sau khi đã union -- áp dụng
    nhất quán cho cả kết quả từ tag lẫn từ text, không còn để lọt qua nhánh tag.
    """
    structure = registry_entry.get("skill_tag_structure")

    tag_based_all = _extract_skills_from_tags(record, structure)
    text_based_all = _extract_skills_from_text(record)

    # Union, deduplicate (giữ nguyên thứ tự) và lọc Noise Skill
    skills_all = [
        s for s in dict.fromkeys(tag_based_all + text_based_all)
        if s not in _NOISE_SKILLS
    ]

    return skills_all