from pipeline.pipeline_steps.shared_clean import clean_text

def test_clean_text_removes_invisible_unicode():
    raw = "Data\xa0Engineer\u200b cần \t Python"
    cleaned = clean_text(raw)
    assert cleaned == "Data Engineer  cần   Python" # \xa0, \u200b và \t biến thành khoảng trắng

def test_clean_text_normalizes_bullets():
    raw = """Yêu cầu:
• Python
▪ SQL
➢ Docker
✓ Kubernetes
* Airflow
+ AWS"""
    cleaned = clean_text(raw)
    expected = """Yêu cầu:
- Python
- SQL
- Docker
- Kubernetes
- Airflow
- AWS"""
    assert cleaned == expected

def test_clean_text_compresses_whitespace_and_newlines():
    raw = "Dòng 1\n\n\n\nDòng 2    nhiều     khoảng     trắng"
    cleaned = clean_text(raw)
    expected = "Dòng 1\n\nDòng 2 nhiều khoảng trắng"
    assert cleaned == expected
def test_clean_text_removes_invisible_unicode():
    raw = "Data\xa0Engineer\u200b cần \t Python"
    cleaned = clean_text(raw)
    # Cập nhật: Kỳ vọng chuỗi đã được dọn sạch và gom khoảng trắng
    assert cleaned == "Data Engineer cần Python"