from pipeline.pipeline_steps.shared_salary_convert import parse_and_convert_salary

def test_convert_vnd_millions_range():
    # Case TopCV phổ biến
    assert parse_and_convert_salary("20 - 30 triệu") == (20.0, 30.0)

def test_convert_usd_range():
    # Case ITviec phổ biến (1 USD = 25.4 tr)
    # 1000 USD -> 25.4 tr, 2000 USD -> 50.8 tr
    assert parse_and_convert_salary("1000 - 2000 USD") == (25.4, 50.8)
    assert parse_and_convert_salary("$1500 - $2500") == (38.1, 63.5)

def test_convert_up_to():
    # Lương chỉ có cận trên
    assert parse_and_convert_salary("Lên đến 1500$") == (None, 38.1)
    assert parse_and_convert_salary("Tới 40 triệu") == (None, 40.0)

def test_convert_full_vnd_zeros():
    # Nhà tuyển dụng nhập dư số 0
    assert parse_and_convert_salary("15,000,000 - 25,000,000 VND") == (15.0, 25.0)

def test_convert_negotiable():
    # Lương thỏa thuận -> Trả về None
    assert parse_and_convert_salary("Thoả thuận") == (None, None)

# === [FIX P0] Ngăn lương 1.2 tỷ / lỗi nghìn ===
def test_convert_annual_usd_50000_year():
    # [FIX P0] "$50,000/year" trước đây ra 1.27 tỷ/tháng (thiếu chia 12).
    # $50,000/năm = 50,000 * 25.4 / 12 = 105,833 VNĐ nghìn/năm -> 105.8 triệu/tháng.
    assert parse_and_convert_salary("$50,000/year") == (105.8, 105.8)

def test_convert_annual_usd_with_annual_keyword():
    # "annual" cũng phải chia 12
    assert parse_and_convert_salary("$120,000 annual") == (254.0, 254.0)

def test_convert_thousand_usd():
    # [FIX P0] "15 - 20 nghìn USD" trước đây parse thành 15-20 USD (lệch 1000×).
    # 15 * 1000 * 25.4 / 1000 = 381 triệu; 20 * 1000 * 25.4 / 1000 = 508 triệu.
    assert parse_and_convert_salary("15 - 20 nghìn USD") == (381.0, 508.0)

def test_convert_thousand_vnd():
    # "20 - 30 nghìn" (không có đơn vị tiền tệ) -> không đoán mò, trả None
    assert parse_and_convert_salary("20 - 30 nghìn") == (None, None)

def test_convert_competitive_vietnamese():
    # [FIX P0] "Cạnh tranh" (TopCV) phải coi là negotiable, không cố parse số.
    assert parse_and_convert_salary("Cạnh tranh") == (None, None)

def test_convert_competitive_english():
    # "Competitive" (ITviec) cũng là negotiable
    assert parse_and_convert_salary("Competitive") == (None, None)

# === [FIX P1] Các marker negotiable mở rộng ===
def test_convert_negotiable_extended_markers():
    for marker in ("thỏa thuận lương", "lương thỏa thuận", "trao đổi",
                   "upon agreement", "k thỏa thuận", "theo thỏa thuận"):
        assert parse_and_convert_salary(marker) == (None, None), f"{marker} should be negotiable"

# === [FIX P1] Strip prefix "Lương:" ===
def test_convert_strip_luong_prefix():
    assert parse_and_convert_salary("Lương: 20 - 30 triệu") == (20.0, 30.0)
    assert parse_and_convert_salary("Lương: 1000 - 2000 USD") == (25.4, 50.8)

# === [FIX P1] "k" viết tắt nghìn (không cách trước k) ===
def test_convert_thousand_k_no_space():
    # "15k USD" -> 15 * 1000 * 25.4/1000 = 381 triệu
    assert parse_and_convert_salary("15k USD") == (381.0, 381.0)
    # "20k - 30k USD" -> 20*1000*0.0254=508, 30*1000*0.0254=762
    assert parse_and_convert_salary("20k - 30k USD") == (508.0, 762.0)

# === [FIX P1] Rate-based salary (hour/day/week) -> None ===
def test_convert_rate_based_returns_none():
    for raw in ("$25/hour", "200.000 VND/ngày", "$500/tuần", "per day 100$"):
        assert parse_and_convert_salary(raw) == (None, None), f"{raw} should return None"
