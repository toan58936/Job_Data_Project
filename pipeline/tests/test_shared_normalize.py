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