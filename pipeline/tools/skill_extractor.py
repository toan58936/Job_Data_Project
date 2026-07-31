from typing import Any, Optional

from pipeline.config.skills_taxonomy import SKILLS_TAXONOMY


def _build_alias_lower_map() -> dict[str, str]:
    alias_map: dict[str, str] = {}
    for entry in SKILLS_TAXONOMY.values():
        canonical = entry["canonical"]
        for alias in entry["aliases"]:
            alias_map[alias.lower()] = canonical
    return alias_map


_ALIAS_LOWER_MAP = _build_alias_lower_map()

# Cache KeywordProcessor ở module-level: trước đây bị build lại (duyệt toàn bộ
# SKILLS_TAXONOMY, add_keyword từng alias) MỖI LẦN gọi extract_skills() cho một
# bản ghi rơi vào nhánh fallback. Với batch vài trăm/nghìn job, đây là chi phí CPU
# lặp lại vô ích cho cùng 1 kết quả. Build 1 lần, dùng lại cho toàn batch.
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


def canonicalize_skill(skill: str) -> str:
    lowered = skill.strip().lower()
    if lowered in _ALIAS_LOWER_MAP:
        return _ALIAS_LOWER_MAP[lowered]
    return skill.strip()


def canonicalize_skills_list(skills: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for s in skills:
        c = canonicalize_skill(s)
        if c not in seen:
            seen.add(c)
            result.append(c)
    return result


def _extract_skills_from_tags(record: Any, structure: Optional[str]) -> dict:
    """Đọc skill từ tag có cấu trúc trong source_extra (nếu nguồn có hỗ trợ và
    bản ghi này thực sự có điền tag). Trả về rỗng nếu không tìm thấy gì — KHÔNG
    coi đó là lỗi, để _extract_skills_from_text() xử lý tiếp."""
    if structure == "flat":
        raw_skills = record.source_extra.get("skills", [])
        deduped = canonicalize_skills_list(raw_skills)
        return {"skills_all": deduped, "skills_required": deduped, "skills_nice_to_have": []}

    if structure == "grouped":
        req = canonicalize_skills_list(record.source_extra.get("skills_required", []))
        nice = canonicalize_skills_list(record.source_extra.get("skills_nice_to_have", []))
        return {
            "skills_all": list(dict.fromkeys(req + nice)),
            "skills_required": req,
            "skills_nice_to_have": nice,
        }

    return {"skills_all": [], "skills_required": [], "skills_nice_to_have": []}


def _extract_skills_from_text(record: Any) -> dict:
    """Fallback: dò từ khoá kỹ năng (flashtext, theo SKILLS_TAXONOMY) trực tiếp
    trong description_raw + requirements_raw (nếu nguồn có field này trong
    source_extra — TopCV có, không phải nguồn nào cũng có nên dùng .get()).

    Chỉ filter case-sensitive cho exact alias "AI" (2 ký tự), không tác động lên
    các alias dài khác như "Generative AI"/"GenAI"."""
    kp = _get_keyword_processor()

    text_parts = [record.description_raw or ""]
    requirements_raw = record.source_extra.get("requirements_raw", "")
    if requirements_raw:
        text_parts.append(requirements_raw)
    text = " ".join(text_parts)

    if not text.strip():
        return {"skills_all": [], "skills_required": [], "skills_nice_to_have": []}

    matches = kp.extract_keywords(text, span_info=True)
    filtered: list[str] = []
    for canonical, start, end in matches:
        span = text[start:end]
        if len(span) == 2 and span != "AI":
            continue
        filtered.append(canonical)

    deduped = list(dict.fromkeys(filtered))
    deduped = [skill for skill in deduped if skill not in _NOISE_SKILLS]
    return {"skills_all": deduped, "skills_required": deduped, "skills_nice_to_have": []}


def extract_skills(record: Any, registry_entry: dict) -> dict:
    """Trích skill cho 1 bản ghi SourceNormalized.

    Luôn chạy cả nhánh tag và text, rồi union lại. Tag được ưu tiên cho phân loại
    required / nice-to-have, còn text chỉ bổ sung khi tag rỗng hoặc thiếu phần nào.
    """
    structure = registry_entry.get("skill_tag_structure")

    tag_based = _extract_skills_from_tags(record, structure)
    text_based = _extract_skills_from_text(record)

    skills_all = list(dict.fromkeys(tag_based["skills_all"] + text_based["skills_all"]))
    skills_required = tag_based["skills_required"]
    skills_nice_to_have = tag_based["skills_nice_to_have"]

    if not skills_required and not skills_nice_to_have and not tag_based["skills_all"]:
        skills_required = text_based["skills_all"]

    return {
        "skills_all": skills_all,
        "skills_required": skills_required,
        "skills_nice_to_have": skills_nice_to_have,
    }