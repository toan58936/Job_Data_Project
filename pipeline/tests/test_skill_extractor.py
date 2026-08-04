from datetime import date
from types import SimpleNamespace

from pipeline.model.raw_record import RawRecord
from pipeline.sources.itviec import parse as itviec_parse_module
from pipeline.sources.topcv import parse as topcv_parse_module
from pipeline.tools.skill_extractor import _extract_skills_from_text, extract_skills


def _make_record(description_raw: str, requirements_raw: str = "", skills_required=None, skills_nice_to_have=None, source="itviec", job_id="t1"):
    source_extra = {"requirements_raw": requirements_raw}
    if skills_required is not None:
        source_extra["skills_required_raw"] = skills_required
    if skills_nice_to_have is not None:
        source_extra["skills_nice_to_have_raw"] = skills_nice_to_have
    return SimpleNamespace(description_raw=description_raw, source_extra=source_extra, source=source, job_id=job_id)


def test_ai_alias_is_case_sensitive_only_for_exact_two_char_match():
    slogan_only = _make_record("Ai yêu miền Bắc và biết thêm chút ...")
    assert "Generative AI" not in _extract_skills_from_text(slogan_only)

    real_ai_signal = _make_record("Cần kỹ sư dữ liệu làm AI/ML trên nền tảng Spark.")
    result = _extract_skills_from_text(real_ai_signal)
    assert "Generative AI" in result


def test_extract_skills_unions_tag_with_text_fallback():
    record = _make_record(
        "Bạn sẽ làm việc với Airflow, Kubernetes và Python trên các pipeline dữ liệu.",
        skills_required=["Python"],
    )

    result = extract_skills(record, {"skill_tag_structure": "flat"})

    assert "Python" in result
    assert "Airflow" in result
    assert "Kubernetes" in result


def test_taxonomy_covers_high_frequency_pipeline_aliases():
    record = _make_record("We use Kafka, Airflow, PostgreSQL and Git in the data pipeline.")

    result = _extract_skills_from_text(record)

    assert "Kafka" in result
    assert "Airflow" in result
    assert "PostgreSQL" in result
    assert "Git" in result


def test_extract_skills_filters_common_noise_terms():
    # _NOISE_SKILLS chỉ áp dụng ở bước union (extract_skills), không áp dụng ở
    # _extract_skills_from_text — nên test noise phải gọi extract_skills() để
    # đúng thiết kế (xem docstring skill_extractor.py).
    record = _make_record("We need strong English communication, team management, and fresher accepted candidates.")

    result = extract_skills(record, {"skill_tag_structure": "flat"})

    assert "English" not in result
    assert "Team Management" not in result
    assert "Fresher Accepted" not in result


def test_taxonomy_covers_common_data_aliases():
    record = _make_record("We work with Big Data, Data Modeling, Power BI, and Machine Learning.")

    result = _extract_skills_from_text(record)

    assert "Big Data" in result
    assert "Data Modeling" in result
    assert "Power BI" in result
    assert "Machine Learning" in result


def test_itviec_parse_adds_posted_date_parsed(monkeypatch):
    monkeypatch.setattr(
        itviec_parse_module,
        "_parse_detail",
        lambda raw: {
            "title": "Data Engineer",
            "company_name": "Test Co",
            "locations": ["Hà Nội"],
            "description_raw": "Work with Airflow, Kubernetes and Python.",
            "work_mode": None,
            "posted_date_raw": "2 days ago",
            "salary_status": "not_provided",
            "salary_min": None,
            "salary_max": None,
            "source_extra": {
                "skills_raw": ["Python"],
                "job_expertise_raw": [],
                "job_domain_raw": [],
            },
        },
    )
    raw = RawRecord(
        job_id="888",
        source="itviec",
        batch_date="2026-07-31",
        url="https://example.com",
        title_listing="Data Engineer",
        listing_page_num=1,
        listing_position=1,
        raw_html_listing="",
        detail_crawled=True,
        title_detail="Data Engineer",
        raw_html_detail="<html></html>",
    )

    parsed = itviec_parse_module.parse(raw)

    assert "posted_date_parsed" in parsed.source_extra
    assert parsed.source_extra["posted_date_parsed"] == "2026-07-29"


def test_date_parser_handles_english_relative_formats():
    parsed = itviec_parse_module.parse_vietnamese_date("22 hours ago", date(2026, 7, 31))
    assert parsed == date(2026, 7, 31)

    parsed = itviec_parse_module.parse_vietnamese_date("1 day ago", date(2026, 7, 31))
    assert parsed == date(2026, 7, 30)


def test_topcv_parse_includes_skills_after_extraction(monkeypatch):
    monkeypatch.setattr(
        topcv_parse_module,
        "_parse_detail",
        lambda raw: {
            "title": "Data Engineer",
            "company_name": "Test Co",
            "locations": ["Hà Nội"],
            "description_raw": "Work with Airflow, Kubernetes and Python.",
            "work_mode": None,
            "salary_status": "not_provided",
            "salary_min": None,
            "salary_max": None,
            "source_extra": {
                "skills_required_raw": ["Python"],
                "skills_nice_to_have_raw": [],
                "skills_industry_raw": [],
                "requirements_raw": "Airflow, Kubernetes",
            },
        },
    )
    raw = RawRecord(
        job_id="999",
        source="topcv",
        batch_date="2026-07-31",
        url="https://example.com",
        title_listing="Data Engineer",
        listing_page_num=1,
        listing_position=1,
        raw_html_listing="",
        detail_crawled=True,
        title_detail="Data Engineer",
        raw_html_detail="<html></html>",
    )

    parsed = topcv_parse_module.parse(raw)

    assert "Python" in parsed.source_extra["skills_required_raw"]
    assert "Airflow" in parsed.source_extra["requirements_raw"]
    assert "Kubernetes" in parsed.source_extra["requirements_raw"]


def test_parse_rejects_future_posted_date():
    """[FIX P2] posted_date không thể ở tương lai — deadline bị lẫn sẽ bị loại."""
    parsed = itviec_parse_module.parse_vietnamese_date("10/08/2026", date(2026, 8, 1))
    assert parsed is None

    # deadline hợp lệ (tương lai) vẫn parse được khi allow_future=True
    parsed = itviec_parse_module.parse_vietnamese_date("10/08/2026", date(2026, 8, 1), allow_future=True)
    assert parsed == date(2026, 8, 10)
