from typing import Any

from pipeline.config.skills_taxonomy import SKILLS_TAXONOMY, canonicalize_skill


def _build_alias_lower_map() -> dict[str, str]:
    alias_map: dict[str, str] = {}
    for entry in SKILLS_TAXONOMY.values():
        canonical = entry["canonical"]
        for alias in entry["aliases"]:
            alias_map[alias.lower()] = canonical
    return alias_map


_ALIAS_LOWER_MAP = _build_alias_lower_map()


def canonicalize_skill(skill: str) -> str:
    lowered = skill.strip().lower()
    if lowered in _ALIAS_LOWER_MAP:
        return _ALIAS_LOWER_MAP[lowered]
    return skill.strip()


def extract_skills(record: Any, registry_entry: dict) -> dict:
    if not registry_entry["provides_skill_tags"]:
        from flashtext import KeywordProcessor

        kp = KeywordProcessor(case_sensitive=False)
        for entry in SKILLS_TAXONOMY.values():
            for alias in entry["aliases"]:
                kp.add_keyword(alias, entry["canonical"])
        raw_skills = kp.extract_keywords(record.description_raw)
        deduped = list(dict.fromkeys(raw_skills))
        return {"skills_all": deduped, "skills_required": deduped, "skills_nice_to_have": []}

    structure = registry_entry["skill_tag_structure"]
    if structure == "flat":
        raw_skills = record.source_extra.get("skills", [])
        deduped = list(dict.fromkeys(raw_skills))
        return {"skills_all": deduped, "skills_required": deduped, "skills_nice_to_have": []}
    if structure == "grouped":
        req = record.source_extra.get("skills_required", [])
        nice = record.source_extra.get("skills_nice_to_have", [])
        return {
            "skills_all": req + nice,
            "skills_required": req,
            "skills_nice_to_have": nice,
        }

    return {"skills_all": [], "skills_required": [], "skills_nice_to_have": []}


def canonicalize_skills_list(skills: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for s in skills:
        c = canonicalize_skill(s)
        if c not in seen:
            seen.add(c)
            result.append(c)
    return result
