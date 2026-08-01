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