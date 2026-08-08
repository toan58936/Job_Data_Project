"""Tests cho seniority_extractor.py — Phần B: Seniority Level Normalization.

Verifies:
- Phân loại seniority từ title tiếng Anh (Senior, Junior, Lead, Director, VP, Fresher, Intern).
- Phân loại seniority từ title tiếng Việt (Chuyên gia, Trưởng nhóm, Giám đốc, Thực tập).
- Ưu tiên mức cao nhất khi title kết hợp nhiều từ khóa (Senior/Lead -> senior).
- Chống false positive (seniority/senior-level không phải senior; team lead -> lead).
- Fallback sang description khi title không có tín hiệu.
- seniority_levels() trả đúng thứ tự.
"""
from pipeline.tools.seniority_extractor import extract_seniority, seniority_levels


def test_english_title_senior():
    assert extract_seniority("Senior Data Engineer") == "senior"
    assert extract_seniority("Sr. Backend Engineer") == "senior"


def test_english_title_junior():
    assert extract_seniority("Junior Data Analyst") == "junior"
    assert extract_seniority("Jr. Frontend Developer") == "junior"


def test_english_title_lead():
    assert extract_seniority("Lead Data Engineer") == "lead"
    assert extract_seniority("Technical Lead") == "lead"


def test_english_title_director_and_vp():
    assert extract_seniority("Director of Engineering") == "director"
    assert extract_seniority("VP of Engineering") == "director"
    assert extract_seniority("Head of Data") == "director"


def test_english_title_fresher_and_intern():
    assert extract_seniority("Fresher Java Developer") == "fresher"
    assert extract_seniority("Data Engineer Intern") == "fresher"


def test_vietnamese_title_expert():
    assert extract_seniority("Chuyên gia tích hợp dữ liệu") == "expert"


def test_vietnamese_title_team_lead():
    assert extract_seniority("Trưởng nhóm kỹ thuật") == "lead"


def test_vietnamese_title_manager_and_director():
    assert extract_seniority("Trưởng phòng quản lý dự án") == "manager"
    assert extract_seniority("Giám đốc công nghệ") == "director"


def test_vietnamese_title_intern():
    assert extract_seniority("Thực tập sinh dữ liệu") == "fresher"


def test_highest_priority_when_multiple_keywords():
    # "Senior/Lead" -> chọn mức cao nhất (lead > senior theo thứ tự ưu tiên)
    assert extract_seniority("Senior/Lead Data Engineer") == "lead"
    # "Middle/Senior" -> senior (senior > middle)
    assert extract_seniority("Middle/Senior Data Engineer") == "senior"


def test_no_false_positive_seniority_vs_senior():
    # "seniority" không phải "senior" (dùng \b)
    assert extract_seniority("Seniority Level Analysis") is None


def test_team_lead_is_lead():
    # "team lead" vẫn là lead
    assert extract_seniority("Team Lead Data") == "lead"


def test_fallback_to_description():
    # Title không có tín hiệu, nhưng description có "Senior"
    assert extract_seniority("Data Engineer", "Chúng tôi cần 1 Senior Data Engineer 5 năm kinh nghiệm.") == "senior"


def test_no_signal_returns_none():
    assert extract_seniority("Data Analyst") is None
    assert extract_seniority("") is None


def test_seniority_levels_order():
    assert seniority_levels() == [
        "fresher", "junior", "middle", "senior", "lead",
        "principal", "expert", "staff", "manager", "director",
    ]
