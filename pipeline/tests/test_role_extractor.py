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


def test_fallback_to_requirements_text():
    # Title không có tín hiệu, requirements_text có "Data Engineer"
    assert extract_role("Position", requirements_text="Data Engineer") == "data_engineer"


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


# === [FIX P1] Vietnamese title patterns mở rộng ===
def test_vietnamese_big_data():
    assert extract_role("Chuyên Viên Big Data (Middle)") == "data_engineer"


def test_vietnamese_ky_thuat_du_lieu():
    assert extract_role("Chuyên Viên Kỹ Thuật Dữ Liệu") == "data_engineer"


def test_vietnamese_giai_cuu_du_lieu():
    assert extract_role("Kỹ Sư Giải Cứu Dữ Liệu") == "data_engineer"


def test_head_of_data():
    assert extract_role("Head Of Data") == "data_engineer"


def test_data_solution_consultant():
    assert extract_role("Data Solution Consultant") == "data_engineer"


def test_spark_etl():
    assert extract_role("Spark ETL (Dự Án Chuyển Đổi Số)") == "data_engineer"


def test_xu_ly_du_lieu():
    assert extract_role("Chuyên Viên Xử Lý Dữ Liệu") == "data_analyst"


def test_data_intelligence_lead():
    assert extract_role("Data Intelligence Lead") == "data_analyst"


def test_operations_data_specialist():
    assert extract_role("Senior Operations Data Specialist") == "data_analyst"


def test_vietnamese_phat_trien_giai_phap_cntt():
    assert extract_role("Chuyên Viên Phát Triển Giải Pháp CNTT (Azure, Cloud)") == "software_engineer"


def test_ecom_it_application():
    assert extract_role("Chuyên Viên E-Com IT Application") == "software_engineer"


def test_it_infrastructure():
    assert extract_role("IT Infrastructure Engineer/ Data Center Storage") == "devops_engineer"


def test_it_server_database():
    assert extract_role("IT Server & Database Engineer") == "devops_engineer"


# === [FIX P1] Vietnamese management patterns ===
def test_truong_nhom_ky_thuat():
    assert extract_role("Trưởng Nhóm Kỹ Thuật") == "engineering_manager"


def test_giam_doc_cong_nghe():
    assert extract_role("Giám Đốc Công Nghệ") == "engineering_manager"


def test_cto():
    assert extract_role("CTO") == "engineering_manager"


def test_vietnamese_kien_truc_su_cong_nghe():
    assert extract_role("Kiến Trúc Sư Công Nghệ") == "solution_architect"


# === [FIX P1] requirements_text fallback (TopCV không có expertise field) ===
def test_fallback_requirements_text():
    # Title không match, requirements_text có "data engineer"
    assert extract_role(
        "Tìm việc làm nhanh 24h", requirements_text="Chúng tôi cần tuyển Data Engineer"
    ) == "data_engineer"


def test_fallback_requirements_not_used_when_title_matches():
    # Title đã match, requirements_text không ảnh hưởng
    assert extract_role(
        "Data Engineer", requirements_text="Chuyên viên phân tích dữ liệu"
    ) == "data_engineer"
