"""Tests cho cross_source_dedupe.py — fix P2 từ elt_audit_report 2026-08-03.

Audit chỉ ra False Positive: 2 job cùng title "Software Engineer" + công ty Viettel
nhưng lương chênh 3x (Junior 15-20tr vs Senior 40-55tr) bị gộp nhầm thành 1.

Fix: thêm `_salary_compatible()` — nếu lương chênh > 50% thì KHÔNG gộp.
"""
from pipeline.model.job_posting import JobPosting, SalaryStatus
from pipeline.pipeline_steps.cross_source_dedupe import _salary_compatible, deduplicate


def _make_posting(job_id, title, company, salary_min, salary_max, description="desc", locations=("Hà Nội",)):
    return JobPosting(
        job_id=job_id,
        source="itviec",
        url=f"https://itviec.com/jobs/{job_id}",
        title=title,
        company_name=company,
        locations=list(locations),
        work_mode="onsite",
        description_raw=description,
        salary_status=SalaryStatus.DISCLOSED,
        salary_min=salary_min,
        salary_max=salary_max,
        job_skills=[],
        source_extra={},
    )


def test_salary_compatible_returns_true_for_similar_salary():
    """Cùng mức lương → tương thích (gộp được)."""
    a = _make_posting("a1", "Software Engineer", "Viettel", 15.0, 20.0)
    b = _make_posting("b1", "Software Engineer", "Viettel", 14.0, 22.0)
    assert _salary_compatible(a, b) is True


def test_salary_compatible_returns_false_for_3x_difference():
    """▶ P2: Lương chênh 3x (Junior vs Senior) → KHÔNG gộp (False Positive)."""
    junior = _make_posting("j", "Software Engineer", "Viettel", 15.0, 20.0)
    senior = _make_posting("s", "Software Engineer", "Viettel", 40.0, 55.0)
    assert _salary_compatible(junior, senior) is False


def test_salary_compatible_true_when_no_salary_data():
    """Cả 2 không có lương → không đủ tín hiệu → coi như tương thích (không chặn)."""
    a = _make_posting("a2", "Software Engineer", "Viettel", None, None)
    b = _make_posting("b2", "Software Engineer", "Viettel", None, None)
    assert _salary_compatible(a, b) is True


def test_salary_compatible_true_when_one_side_missing():
    """1 bên không có lương → không đủ tín hiệu → tương thích."""
    a = _make_posting("a3", "Software Engineer", "Viettel", 15.0, 20.0)
    b = _make_posting("b3", "Software Engineer", "Viettel", None, None)
    assert _salary_compatible(a, b) is True


def test_deduplicate_keeps_same_company_different_salary():
    """▶ P2: Dedup không gộp 2 job cùng title/công ty nhưng lương khác level."""
    junior = _make_posting("j2", "Software Engineer", "Viettel", 15.0, 20.0)
    senior = _make_posting("s2", "Software Engineer", "Viettel", 40.0, 55.0)
    result = deduplicate([junior, senior])
    assert len(result) == 2


def test_deduplicate_merges_similar_salary_same_title():
    """Cùng title + công ty + lương tương đương → vẫn gộp được (không phá hạnh phúc)."""
    a = _make_posting("a4", "Software Engineer", "Viettel", 15.0, 20.0)
    b = _make_posting("b4", "Software Engineer", "Viettel", 16.0, 21.0)
    result = deduplicate([a, b])
    assert len(result) == 1
