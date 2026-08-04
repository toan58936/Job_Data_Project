"""Tests cho role_extractor.py — chuẩn hóa Job Role (canonical) cho dashboard.

Verifies:
- Bóc tách role từ title tiếng Anh (Data Engineer, Data Analyst, ML Engineer...).
- Bóc tách role từ title tiếng Việt (Kỹ sư dữ liệu, Chuyên viên phân tích...).
- Ưu tiên role cụ thể hơn khi title có nhiều từ khóa (SRE là devops, không phải software).
- Fallback sang expertise khi title không có tín hiệu.
- Không false positive (data trong database, analyst trong analytics).
"""
from pipeline.tools.role_extractor import extract_role, job_roles


def test_english_data_engineer():
    assert extract_role("Senior Data Engineer") == "data_engineer"
    assert extract_role("Data Integration Engineer") == "data_engineer"
    assert extract_role("Data Platform Engineer") == "data_engineer"


def test_english_data_analyst():
    assert extract_role("Data Analyst") == "data_analyst"
    assert extract_role("BI Analyst") == "data_analyst"
    assert extract_role("Power BI Developer") == "data_analyst"


def test_english_data_scientist():
    assert extract_role("Data Scientist") == "data_scientist"
    assert extract_role("Data Science Lead") == "data_scientist"


def test_english_ml_engineer():
    assert extract_role("Machine Learning Engineer") == "ml_engineer"
    assert extract_role("MLOps Engineer") == "ml_engineer"


def test_english_devops_sre():
    assert extract_role("DevOps Engineer") == "devops_engineer"
    assert extract_role("SRE") == "devops_engineer"
    assert extract_role("Cloud Engineer") == "devops_engineer"


def test_english_qa():
    assert extract_role("QA Engineer") == "qa_engineer"
    assert extract_role("Tester") == "qa_engineer"


def test_vietnamese_data_engineer():
    assert extract_role("Kỹ sư dữ liệu") == "data_engineer"
    assert extract_role("Chuyên gia tích hợp dữ liệu") == "data_engineer"


def test_vietnamese_data_analyst():
    assert extract_role("Chuyên viên phân tích dữ liệu") == "data_analyst"
    assert extract_role("Phân tích dữ liệu") == "data_analyst"


def test_vietnamese_data_scientist():
    assert extract_role("Chuyên gia khoa học dữ liệu") == "data_scientist"


def test_specific_role_preferred_over_generic():
    # "SRE" là devops, không bị nuốt thành software_engineer
    assert extract_role("SRE") == "devops_engineer"
    # "Backend Engineer" -> backend, không phải software chung
    assert extract_role("Senior Backend Engineer") == "backend_engineer"


def test_fallback_to_expertise():
    # Title không có tín hiệu, nhưng expertise có "Data Engineer"
    assert extract_role("Position", ["Data Engineer"]) == "data_engineer"


def test_no_false_positive_database():
    # "database" không phải "data" role (dùng \b)
    assert extract_role("Database Administrator") is None


def test_no_signal_returns_none():
    assert extract_role("") is None
    assert extract_role("Manager") is None or extract_role("Manager") == "engineering_manager"


def test_job_roles_order():
    roles = job_roles()
    assert "data_engineer" in roles
    assert "data_analyst" in roles
    assert "data_scientist" in roles
    # data_engineer nên được đặt trước data_analyst (ưu tiên cụ thể)
    assert roles.index("data_engineer") < roles.index("data_analyst")
