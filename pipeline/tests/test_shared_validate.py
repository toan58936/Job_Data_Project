"""Tests cho shared_validate.py — các fix từ elt_audit_report 2026-08-03.

Báo cáo audit chỉ ra:
- 3.1% locations rỗng, 7.1% work_mode rỗng → trước đây không validate required.
- 4 job status=disclosed nhưng thiếu salary_min/max (itv_3847, itv_3902, tcv_8821,
  tcv_9014) → trước đây không flag.

Fix: validate locations/work_mode nhưng KHÔNG reject (chỉ hạ cấp data_completeness),
và flag salary_disclosed_but_missing khi disclosed nhưng thiếu min/max.
"""
from pipeline.model.source_normalized import SalaryStatus, SourceNormalized
from pipeline.pipeline_steps.shared_validate import validate


def _make_record(**overrides) -> SourceNormalized:
    base = dict(
        job_id="t1",
        source="itviec",
        url="https://itviec.com/jobs/1",
        title="Data Engineer",
        company_name="Test Co",
        locations=["Hà Nội"],
        description_raw="Do something",
        posted_date_raw="today",
        salary_status=SalaryStatus.DISCLOSED,
        salary_min=20.0,
        salary_max=30.0,
        work_mode=None,
        source_extra={},
    )
    base.update(overrides)
    return SourceNormalized(**base)


def test_disclosed_with_missing_salary_is_flagged():
    """▶ P1: 4 job disclosed thiếu min/max phải bị flag salary_disclosed_but_missing."""
    rec = _make_record(salary_min=None, salary_max=None)
    result = validate(rec)
    assert "salary_disclosed_but_missing" in result.reasons


def test_disclosed_with_full_salary_not_flagged():
    """Job disclosed có đầy đủ min/max → không flag."""
    rec = _make_record(salary_min=20.0, salary_max=30.0)
    result = validate(rec)
    assert "salary_disclosed_but_missing" not in result.reasons


def test_negotiable_missing_salary_not_flagged():
    """NEGOTIABLE không cần min/max → không phải lỗi."""
    rec = _make_record(salary_status=SalaryStatus.NEGOTIABLE, salary_min=None, salary_max=None)
    result = validate(rec)
    assert "salary_disclosed_but_missing" not in result.reasons


def test_missing_locations_flags_but_keeping_full_description_not_reject():
    """▶ P2: locations rỗng → gắn cờ missing_locations, KHÔNG reject.

    Lưu ý logic data_completeness: khi description_raw có nội dung → vẫn là
    "full" (chỉ hạ xuống "incomplete" khi description rỗng + có flag)."""
    rec = _make_record(locations=[])
    result = validate(rec)
    assert result.is_valid is True
    assert "missing_locations" in rec.source_extra["completeness_flags"]
    assert result.data_completeness == "full"


def test_missing_work_mode_flags_but_keeping_full_description_not_reject():
    """▶ P2: work_mode rỗng → gắn cờ missing_work_mode, KHÔNG reject."""
    rec = _make_record(work_mode=None)
    result = validate(rec)
    assert result.is_valid is True
    assert "missing_work_mode" in rec.source_extra["completeness_flags"]
    assert result.data_completeness == "full"


def test_empty_description_with_missing_fields_is_incomplete():
    """Description rỗng + thiếu locations/work_mode → data_completeness = incomplete."""
    rec = _make_record(description_raw="", locations=[], work_mode=None)
    result = validate(rec)
    assert result.is_valid is True
    assert result.data_completeness == "incomplete"


def test_full_record_is_full_completeness():
    """Record đầy đủ → data_completeness = full, không flag."""
    rec = _make_record(locations=["Hà Nội"], work_mode="onsite")
    result = validate(rec)
    assert result.is_valid is True
    assert result.data_completeness == "full"
    assert rec.source_extra["completeness_flags"] == []


def test_salary_min_gt_max_is_rejected():
    """salary_min > salary_max → vẫn reject (giữ nguyên hành vi cũ)."""
    rec = _make_record(salary_min=50.0, salary_max=10.0)
    result = validate(rec)
    assert "salary_min_gt_max" in result.reasons
    assert result.is_valid is False
