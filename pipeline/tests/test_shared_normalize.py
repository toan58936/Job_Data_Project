from datetime import date

from pipeline.model.source_normalized import SalaryStatus, SourceNormalized
from pipeline.pipeline_steps.shared_normalize import normalize, normalize_locations

def test_normalize_locations_basic_mapping():
    """Kiểm tra mapping cơ bản và không phân biệt hoa thường."""
    raw = ["ha noi", "HCM", "đà nẵng", "hai phong"]
    expected = ["Hà Nội", "Hồ Chí Minh", "Đà Nẵng", "Hải Phòng"]
    assert normalize_locations(raw) == expected

def test_normalize_locations_complex_topcv_string():
    """Kiểm tra khả năng bóc tách từ chuỗi dài lộn xộn của TopCV."""
    raw = [
        "Hà Nội: Keangnam Landmark, Phường Từ Liêm",
        "Hồ Chí Minh: Tòa nhà Bitexco, Quận 1",
        "Bình Dương: KCN VSIP 1"
    ]
    expected = ["Hà Nội", "Hồ Chí Minh", "Bình Dương"]
    assert normalize_locations(raw) == expected

def test_normalize_locations_deduplication():
    """Kiểm tra tính năng khử trùng lặp (chỉ lấy 1 tên tỉnh thành duy nhất)."""
    # Ví dụ job yêu cầu làm ở 3 cơ sở nhưng đều thuộc Hà Nội
    raw = ["Hà Nội: Cầu Giấy", "Ha Noi", "HN", "Đà Nẵng"]
    expected = ["Hà Nội", "Đà Nẵng"]
    assert normalize_locations(raw) == expected

def test_normalize_locations_fallback_unknown():
    """Kiểm tra fallback: Nếu là tỉnh thành lạ chưa có trong Map thì làm sạch khoảng trắng rồi giữ nguyên."""
    raw = ["Sao Hỏa", "   Bắc    Giang   "]
    expected = ["Sao Hỏa", "Bắc Giang"]
    assert normalize_locations(raw) == expected


def test_normalize_locations_full_province_list():
    """[P2] 63 tỉnh/thành phải được chuẩn hóa, kể cả biến thể không dấu/tiếng Anh."""
    raw = [
        "Tây Ninh",
        "Tay Ninh",
        "Quảng Ninh",
        "Bắc Giang",
        "Thái Nguyên",
        "Đắk Lắk",
        "Kon Tum",
        "Lâm Đồng",
        "Bà Rịa - Vũng Tàu",
        "Bà Rịa Vũng Tàu",
    ]
    expected = [
        "Tây Ninh",
        "Quảng Ninh",
        "Bắc Giang",
        "Thái Nguyên",
        "Đắk Lắk",
        "Kon Tum",
        "Lâm Đồng",
        "Bà Rịa - Vũng Tàu",
    ]
    assert normalize_locations(raw) == expected


def test_normalize_locations_prefix_slice():
    """[P2] Chuỗi "Tỉnh: (chi tiết)" hoặc "Tỉnh - (chi tiết)" phải cắt về đúng tên tỉnh."""
    raw = [
        "Quảng Ninh: (Tất cả phường)",
        "Hà Nội - 123 Đường Láng, Đống Đa",
        "Bình Dương: KCN VSIP 1",
    ]
    expected = ["Quảng Ninh", "Hà Nội", "Bình Dương"]
    assert normalize_locations(raw) == expected


def test_normalize_locations_english_variants():
    """[P2] Biến thể tiếng Anh/không dấu của các tỉnh cũng được map."""
    raw = ["Ha Noi", "Ho Chi Minh", "Da Nang", "Hai Phong", "Can Tho", "Quang Ninh"]
    expected = ["Hà Nội", "Hồ Chí Minh", "Đà Nẵng", "Hải Phòng", "Cần Thơ", "Quảng Ninh"]
    assert normalize_locations(raw) == expected


def test_normalize_keeps_existing_posted_date():
    """[Task 4] Nếu parser đã parse posted_date, normalize không ghi đè."""
    rec = SourceNormalized(
        job_id="t1",
        source="itviec",
        batch_date="2026-08-01",
        url="https://itviec.com/jobs/1",
        title="Data Engineer",
        company_name="Test Co",
        locations=["Hà Nội"],
        description_raw="Do something",
        posted_date_raw="3 ngày trước",
        posted_date=date(2026, 7, 29),
        salary_status=SalaryStatus.DISCLOSED,
        salary_min=20.0,
        salary_max=30.0,
        source_extra={},
    )
    result = normalize(rec)
    assert result.posted_date == date(2026, 7, 29)


def test_normalize_parses_posted_date_when_missing():
    """[Task 4] Nếu parser quên posted_date, normalize parse từ posted_date_raw."""
    rec = SourceNormalized(
        job_id="t1",
        source="itviec",
        batch_date="2026-08-01",
        url="https://itviec.com/jobs/1",
        title="Data Engineer",
        company_name="Test Co",
        locations=["Hà Nội"],
        description_raw="Do something",
        posted_date_raw="3 ngày trước",
        posted_date=None,
        salary_status=SalaryStatus.DISCLOSED,
        salary_min=20.0,
        salary_max=30.0,
        source_extra={},
    )
    result = normalize(rec)
    assert result.posted_date == date(2026, 7, 29)
    assert result.source_extra["posted_date_parsed"] == "2026-07-29"


def test_normalize_keeps_none_when_raw_empty():
    """[Task 4] posted_date_raw rỗng → posted_date vẫn None."""
    rec = SourceNormalized(
        job_id="t1",
        source="itviec",
        batch_date="2026-08-01",
        url="https://itviec.com/jobs/1",
        title="Data Engineer",
        company_name="Test Co",
        locations=["Hà Nội"],
        description_raw="Do something",
        posted_date_raw="",
        posted_date=None,
        salary_status=SalaryStatus.DISCLOSED,
        salary_min=20.0,
        salary_max=30.0,
        source_extra={},
    )
    result = normalize(rec)
    assert result.posted_date is None
