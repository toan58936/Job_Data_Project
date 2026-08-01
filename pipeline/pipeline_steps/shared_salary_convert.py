import re
from typing import Optional, Tuple

from pipeline.model.source_normalized import SalaryStatus, SourceNormalized

# Tỷ giá quy đổi (Giả lập: 1 USD = 25,400 VNĐ) — nên chuyển sang đọc từ
# data/metadata/exchange_rate_snapshot.parquet khi có, để không hard-code
# tỷ giá cũ mãi mãi. Giữ hard-code làm fallback nếu snapshot chưa có.
EXCHANGE_RATE_USD_TO_VND = 25.4


def parse_and_convert_salary(salary_raw: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Nhận chuỗi lương thô (VD: '1000 - 1500 USD', 'Trên 20 triệu')
    Quy đổi toàn bộ về định dạng float với đơn vị: Triệu VNĐ.

    [FIX] Đây giờ là NƠI DUY NHẤT tính số lương trong toàn pipeline — parse.py
    (itviec/topcv) không còn tự tính nữa (chỉ trích text thô vào source_extra
    ["salary_raw"]), tránh 2 nơi cùng parse với logic phân kỳ như trước.
    """
    if not salary_raw or salary_raw.lower() in ("thoả thuận", "thỏa thuận", "negotiable", "thương lượng"):
        return None, None

    cleaned = salary_raw.lower().replace(",", "")  # VD: 15,000,000 -> 15000000

    # 1. Xác định hệ số nhân để đưa về "Triệu VNĐ"
    # [FIX] Trước đây multiplier mặc định = 1.0 và KHÔNG thay đổi nếu không khớp
    # bất kỳ đơn vị nào ("usd"/"triệu"/"tr"/"vnd") -- nghĩa là 1 số trần trụi như
    # "15000000" (không có chữ đơn vị đi kèm) bị hiểu nhầm thành "15000000 triệu",
    # một con số vô lý. Giờ nếu không nhận diện được đơn vị, trả None thay vì đoán.
    multiplier: Optional[float] = None

    if "usd" in cleaned or "$" in cleaned:
        # Ví dụ 1000 USD -> 1000 * (25.4 / 1000) = 25.4 triệu VNĐ
        multiplier = EXCHANGE_RATE_USD_TO_VND / 1000
    elif "triệu" in cleaned or re.search(r"\d+\s*tr\b", cleaned) or re.search(r"\btr\b", cleaned):
        # [FIX] Trước đây check "tr" in cleaned (substring bất kỳ đâu trong chuỗi) --
        # rủi ro khớp nhầm các từ chứa "tr" không liên quan đến đơn vị tiền. Giờ chỉ
        # nhận "triệu" đầy đủ, hoặc "tr" đứng riêng/dính liền sau số (dạng viết tắt
        # "20tr").
        multiplier = 1.0
    elif "vnd" in cleaned or "vnđ" in cleaned:
        # Ví dụ ghi hẳn 15000000 VND -> 15000000 * (1/1000000) = 15 triệu
        multiplier = 1 / 1_000_000

    if multiplier is None:
        return None, None

    # 2. Tìm tất cả các con số trong chuỗi (Hỗ trợ cả số thập phân như 1.5)
    numbers = re.findall(r"(\d+(?:\.\d+)?)", cleaned.replace(",", "."))
    if not numbers:
        return None, None

    # Áp dụng hệ số quy đổi và làm tròn 1 chữ số thập phân
    vals = [round(float(n) * multiplier, 1) for n in numbers]

    # 3. Phân loại cấu trúc (Khoảng, Cận dưới, Cận trên)
    if "-" in cleaned or " tới " in cleaned or " đến " in cleaned:
        if len(vals) >= 2:
            return vals[0], vals[1]

    if re.search(r"tới|lên đến|up to|max", cleaned):
        return None, vals[0]

    if re.search(r"từ|trên|min|over", cleaned):
        return vals[0], None

    # Nếu chỉ có 1 số đứng trơ trọi (Fix cứng lương)
    if len(vals) == 1:
        return vals[0], vals[0]

    return None, None


def convert_salary(record: SourceNormalized) -> SourceNormalized:
    """
    Bước 4 Pipeline: Đọc salary_raw từ source_extra (do parse.py trích ra, KHÔNG
    tự tính số), tính toán và ghi salary_min/salary_max bằng Triệu VNĐ.

    [FIX] Trước đây salary_raw không bao giờ được điền (parse.py chưa từng ghi
    field này vào source_extra) -- hàm này thực chất là no-op trên mọi record dù
    logic quy đổi USD bên trong đúng. Cần áp dụng patch parse.py đi kèm (xem
    HUONG_DAN_SUA_parse_py_salary.txt) để salary_raw có giá trị thật, nếu không
    hàm này vẫn tiếp tục là dead code sau khi vá file này.
    """
    salary_raw = record.source_extra.get("salary_raw", "")

    if record.salary_status == SalaryStatus.DISCLOSED and salary_raw:
        min_val, max_val = parse_and_convert_salary(salary_raw)
        if min_val is not None or max_val is not None:
            record.salary_min = min_val
            record.salary_max = max_val

    return record