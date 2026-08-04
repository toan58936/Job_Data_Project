from pipeline.pipeline_steps.shared_normalize import normalize_locations

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
