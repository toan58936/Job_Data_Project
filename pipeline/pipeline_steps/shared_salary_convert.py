"""
shared_salary_convert.py — Bước 4 Pipeline: Quy đổi lương thô về "Triệu VNĐ / tháng".

[FIX P0 — elt_audit_report 2026-08-03]
1. Xử lý đơn vị "nghìn" / "ngàn" / "thousand" / "k":
   - Trước đây "15 - 20 nghìn USD" bị parse thành 15-20 USD (thiếu hệ số ×1000),
     gây lệch ~1000 lần so với thực tế.
2. Xử lý lương quy theo NĂM (year / năm / annual):
   - Trước đây "$50,000/year" bị nhân thẳng tỷ giá thành ~1.27 tỷ VNĐ/tháng
     (bug gốc của job itv_3891: salary_max = 1.2 tỷ), thiếu bước chia 12.
3. Tỷ giá USD không còn hardcode duy nhất:
   - Ưu tiên đọc snapshot `data/metadata/exchange_rate_snapshot.json` (.parquet),
     nếu không có thì fallback về hằng số 25.4 (25,400 VNĐ/USD).
4. Thêm "Cạnh tranh" / "Competitive" vào danh sách negotiable:
   - Trước đây TopCV ghi "Cạnh tranh" bị phân loại DISCLOSED → không lương.
"""
import json
import logging
import re
from pathlib import Path
from typing import Optional, Tuple

from pipeline.model.source_normalized import SalaryStatus, SourceNormalized

logger = logging.getLogger(__name__)

# Tỷ giá quy đổi FALLBACK (1 USD = 25,400 VNĐ, đơn vị lưu = nghìn VNĐ).
# Ưu tiên đọc từ snapshot: data/metadata/exchange_rate_snapshot.json hoặc .parquet.
DEFAULT_EXCHANGE_RATE_USD_TO_VND = 25.4

# Tên cũ giữ lại để tương thích nếu nơi khác import trực tiếp hằng số này.
EXCHANGE_RATE_USD_TO_VND = DEFAULT_EXCHANGE_RATE_USD_TO_VND

_EXCHANGE_RATE_CACHE: Optional[float] = None

# Các chuỗi "không có mức lương cụ thể" -> trả về (None, None).
# [FIX P0] Bổ sung "cạnh tranh"/"competitive" — TopCV dùng khi không muốn
# công khai số, phải coi như negotiable thay vì cố parse số.
_NEGOTIABLE_MARKERS = frozenset({
    "thoả thuận", "thỏa thuận", "thương lượng", "negotiable",
    "competitive", "cạnh tranh",
    "thỏa thuận lương", "lương thỏa thuận", "trao đổi",
    "upon agreement", "k thỏa thuận", "theo thỏa thuận",
})


def get_exchange_rate() -> float:
    """Trả tỷ giá USD->VNĐ (đơn vị: nghìn VNĐ / 1 USD), ưu tiên snapshot nếu có.

    Thứ tự ưu tiên:
      1. data/metadata/exchange_rate_snapshot.json  (field `usd_to_vnd_k` hoặc `usd_to_vnd`)
      2. data/metadata/exchange_rate_snapshot.parquet (cột `usd_to_vnd_k`)
      3. Fallback: DEFAULT_EXCHANGE_RATE_USD_TO_VND (25.4)
    """
    global _EXCHANGE_RATE_CACHE
    if _EXCHANGE_RATE_CACHE is not None:
        return _EXCHANGE_RATE_CACHE

    rate = DEFAULT_EXCHANGE_RATE_USD_TO_VND

    # 1. Snapshot JSON (nhẹ, không cần pandas)
    try:
        json_path = Path("data/metadata/exchange_rate_snapshot.json")
        if json_path.exists():
            data = json.loads(json_path.read_text(encoding="utf-8"))
            # Hỗ trợ cả 2 kiểu: usd_to_vnd_k = 25.4 (nghìn VNĐ) hoặc usd_to_vnd = 25400 (VNĐ)
            candidate = float(data.get("usd_to_vnd_k", data.get("usd_to_vnd", 0) / 1000))
            if candidate > 0:
                rate = candidate
    except Exception:
        pass

    # 2. Snapshot Parquet (cần pandas/pyarrow — nếu chưa cài thì bỏ qua âm thầm)
    if rate == DEFAULT_EXCHANGE_RATE_USD_TO_VND:
        try:
            parquet_path = Path("data/metadata/exchange_rate_snapshot.parquet")
            if parquet_path.exists():
                import pandas as pd
                df = pd.read_parquet(parquet_path)
                if not df.empty:
                    candidate = float(df.iloc[0]["usd_to_vnd_k"])
                    if candidate > 0:
                        rate = candidate
        except Exception:
            pass

    _EXCHANGE_RATE_CACHE = rate
    return rate


def parse_and_convert_salary(salary_raw: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Nhận chuỗi lương thô (VD: '1000 - 1500 USD', 'Trên 20 triệu')
    Quy đổi toàn bộ về định dạng float với đơn vị: Triệu VNĐ.

[FIX] Đây giờ là NƠI DUY NHẤT tính số lương trong toàn pipeline — parse.py
    (itviec/topcv) không còn tự tính nữa (chỉ trích text thô vào source_extra
["salary_raw"]), tránh 2 nơi cùng parse với logic phân kỳ như trước.
    """
    if not salary_raw or salary_raw.strip().lower() in _NEGOTIABLE_MARKERS:
        return None, None

    cleaned = salary_raw.lower()

    # [FIX P1] Loại bỏ prefix "Lương:" / "Lương -" thường gặp (không ảnh hưởng số)
    cleaned = re.sub(r"^(lương\s*[:\-]?\s*)", "", cleaned)

    # [FIX] Xử lý an toàn dấu phẩy/chấm phân cách hàng nghìn (VD: 1.500 USD, 15,000,000 VND)
    # Lặp để xóa dấu phân cách hàng nghìn (dấu chấm/phẩy theo sau bởi đúng 3 chữ số và kết thúc từ)
    while re.search(r'(\d)[.,](\d{3})\b', cleaned):
        cleaned = re.sub(r'(\d)[.,](\d{3})\b', r'\1\2', cleaned)

    # Loại bỏ các dấu phẩy còn sót (nếu có, không thuộc dạng hàng nghìn)
    cleaned = cleaned.replace(",", "")

    # 1. Xác định trạng thái đơn vị để quy đổi về "Triệu VNĐ"
    has_usd = "usd" in cleaned or "$" in cleaned
    has_million = ("triệu" in cleaned or re.search(r"\d+\s*tr\b", cleaned)
                   or re.search(r"\btr\b", cleaned) or "million" in cleaned)
    has_vnd = "vnd" in cleaned or "vnđ" in cleaned
    # [FIX P1] "k" viết tắt nghìn: dùng regex để bắt cả "15k USD" (k dính số)
    # và "15 k USD" (k tách rời). \bk\b không match "15k" vì thiếu word boundary
    # giữa digit và k -> thêm alternation (?:\d|\b) để cover cả 2 trường hợp.
    has_thousand = (
        any(w in cleaned for w in ("nghìn", "ngàn", "thousand"))
        or re.search(r"(?:\d|\b)k\b", cleaned) is not None
    )

    # [FIX P0] "nghìn"/"ngàn" mà KHÔNG kèm đơn vị tiền tệ (USD/VND/triệu) -> không
    # đoán mò, trả None. Trước đây "20 - 30 nghìn" bị nhân 1/1000 ra 0.02-0.03 triệu.
    if has_thousand and not (has_usd or has_million or has_vnd):
        return None, None

    if has_usd:
        # Ví dụ 1000 USD -> 1000 * (25.4 / 1000) = 25.4 triệu VNĐ
        multiplier = EXCHANGE_RATE_USD_TO_VND / 1000
    elif has_million:
        # [FIX] Trước đây check "tr" in cleaned (substring bất kỳ đâu trong chuỗi) --
        # rủi ro khớp nhầm các từ chứa "tr" không liên quan đến đơn vị tiền. Giờ chỉ
        # nhận "triệu" đầy đủ, hoặc "tr" đứng riêng/dính liền sau số (dạng viết tắt
        # "20tr").
        multiplier = 1.0
    elif has_vnd:
        # Ví dụ ghi hẳn 15000000 VND -> 15000000 * (1/1000000) = 15 triệu
        multiplier = 1 / 1_000_000
    else:
        # Không nhận diện được đơn vị -> không đoán, trả None (tránh con số vô lý)
        return None, None

    # [FIX P0] "nghìn" / "ngàn" / "thousand" -> nhân 1000 (15 nghìn USD = 15,000 USD)
    if has_thousand:
        multiplier = multiplier * 1000

    # [FIX P0] Lương quy theo NĂM (year / năm / annual) -> chia 12 để về theo tháng
    is_yearly = any(word in cleaned for word in
                    ["/year", "/ year", "năm", "per year", "yearly", "annually", "annual", "p.a"])
    if is_yearly:
        multiplier = multiplier / 12

    # [FIX P1] Lương tính theo GIỜ/NGÀY/TUẦN -> không thể quy về tháng mà không biết
    # lịch làm việc. Log warning + trả về None thay vì đoán nhầm.
    is_rate_based = any(word in cleaned for word in
                        ["/hour", "/giờ", "/day", "/ngày", "/week", "/tuần",
                         "per hour", "per day", "per week",
                         "hourly", "daily", "weekly"])
    if is_rate_based:
        logger.warning("Rate-based salary '%s' — cannot convert without work-schedule context", salary_raw)
        return None, None

    # 2. Tìm tất cả các con số trong chuỗi (Hỗ trợ cả số thập phân như 1.5)
    numbers = re.findall(r"(\d+(?:\.\d+)?)", cleaned.replace(",", "."))
    if not numbers:
        return None, None

    # Quy đổi và làm tròn 1 chữ số thập phân (đơn vị: Triệu VNĐ)
    vals = [round(float(n) * multiplier, 1) for n in numbers]

    # 3. Phân loại cấu trúc (Khoảng, Cận dưới, Cận trên)
    if "-" in cleaned or " tới " in cleaned or " đến " in cleaned:
        if len(vals) >= 2:
            return min(vals[0], vals[1]), max(vals[0], vals[1])
    if re.search(r"tới|lên đến|up to|max|tối đa", cleaned):
        return None, vals[0]

    if re.search(r"từ|trên|min|over|tối thiểu", cleaned):
        return vals[0], None

    # Nếu chỉ có 1 số đứng trơ trọi (mức lương cố định)
    if len(vals) == 1:
        return vals[0], vals[0]

    return None, None


def convert_salary(record: SourceNormalized) -> SourceNormalized:
    """
    Bước 4 Pipeline: Đọc salary_raw từ source_extra (do parse.py trích ra, KHÔNG
    tự tính số), tính toán và ghi salary_min/salary_max bằng Triệu VNĐ / tháng.

    [FIX P0] Nhờ parse_and_convert_salary() đã xử lý "nghìn"/"year"/"cạnh tranh",
    các trường hợp từng rơi vào salary_parse_error hoặc ra giá trị 1.2 tỷ nay được
    quy đổi đúng.
    """
    salary_raw = record.source_extra.get("salary_raw", "")

    if record.salary_status == SalaryStatus.DISCLOSED and salary_raw:
        min_val, max_val = parse_and_convert_salary(salary_raw)
        if min_val is not None or max_val is not None:
            record.salary_min = min_val
            record.salary_max = max_val

    return record

