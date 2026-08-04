"""
Chuyển các chuỗi ngày tháng tiếng Việt (dạng tương đối "3 ngày trước" hoặc
tuyệt đối "19/08/2026") thành đối tượng date thật — dùng cho posted_date_raw
(TopCV/ITviec) và các field ngày tháng khác trong tương lai (application_deadline...).

Thiết kế tách 2 hàm con (tương đối / tuyệt đối) + 1 hàm chính thử cả 2, để dùng
được cho MỌI field ngày tháng của MỌI nguồn sau này — không chỉ riêng
posted_date_raw của TopCV/ITviec hiện tại.
"""
import re
from datetime import date, timedelta
from typing import Optional

# Số ngày xấp xỉ cho "tháng"/"năm" tương đối — chấp nhận sai số vài ngày vì mục
# đích chỉ để phân tích xu hướng theo tuần/tháng, không cần chính xác tuyệt đối.
_APPROX_DAYS_PER_MONTH = 30
_APPROX_DAYS_PER_YEAR = 365

_RELATIVE_UNIT_TO_DAYS = {
    "giờ": 0,
    "hour": 0,
    "hours": 0,
    "ngày": 1,
    "day": 1,
    "days": 1,
    "tuần": 7,
    "week": 7,
    "weeks": 7,
    "tháng": _APPROX_DAYS_PER_MONTH,
    "month": _APPROX_DAYS_PER_MONTH,
    "months": _APPROX_DAYS_PER_MONTH,
    "năm": _APPROX_DAYS_PER_YEAR,
    "year": _APPROX_DAYS_PER_YEAR,
    "years": _APPROX_DAYS_PER_YEAR,
}

_RELATIVE_PATTERN = re.compile(
    r"(\d+)\s*(giờ|hour|hours|ngày|day|days|tuần|week|weeks|tháng|month|months|năm|year|years)\s*(?:ago|trước)?",
    re.IGNORECASE,
)

_ABSOLUTE_PATTERN = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")


def parse_relative_vietnamese(text: str, reference_date: date) -> Optional[date]:
    """"3 ngày trước" / "2 tuần trước" / "hôm nay" / "hôm qua" -> date tuyệt đối,
    tính lùi từ reference_date (= ngày crawl, tức batch_date). Trả về None nếu
    không khớp mẫu nào đã biết — KHÔNG đoán mò, để caller tự quyết định xử lý
    tiếp (giữ nguyên raw, hoặc log cảnh báo)."""
    if not text:
        return None
    cleaned = text.strip().lower()

    if cleaned in ("hôm nay", "today", "vừa xong", "mới đăng"):
        return reference_date
    if cleaned in ("hôm qua", "yesterday"):
        return reference_date - timedelta(days=1)

    match = _RELATIVE_PATTERN.search(cleaned)
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2).lower()
    if unit in {"giờ", "hour", "hours"}:
        return reference_date
    days = amount * _RELATIVE_UNIT_TO_DAYS[unit]
    return reference_date - timedelta(days=days)


def parse_absolute_vietnamese(text: str) -> Optional[date]:
    """"19/08/2026" (dd/mm/yyyy, định dạng phổ biến trên TopCV cho hạn ứng
    tuyển) -> date. Trả về None nếu không khớp hoặc ngày không hợp lệ (ví dụ
    "31/02/2026")."""
    if not text:
        return None
    match = _ABSOLUTE_PATTERN.search(text.strip())
    if not match:
        return None

    day, month, year = (int(g) for g in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_vietnamese_date(text: str, reference_date: date, allow_future: bool = False) -> Optional[date]:
    """Điểm vào chính — thử tuyệt đối trước (rẻ, không mơ hồ), rồi mới thử
    tương đối. Dùng hàm này ở pipeline_steps/ thay vì gọi trực tiếp 2 hàm con,
    trừ khi caller đã biết chắc định dạng (ví dụ posted_date_raw luôn tương
    đối, deadline luôn tuyệt đối) và muốn báo lỗi sớm nếu sai định dạng.

    [FIX P2] Thêm guard `allow_future` (mặc định False = dùng cho posted_date):
    nếu chuỗi ngày tuyệt đối parse ra NẰM TRONG TƯƠNG LAI so với reference_date,
    coi là INVALID (trả None). TopCV đôi khi lẫn ngày "Hạn ứng tuyển" (deadline,
    luôn ở tương lai) vào posted_date_raw — allow_future=False sẽ chặn case này,
    tránh ghi ngày đăng trong tương lai (audit anomaly #9). Với field thật sự là
    ngày tương lai (application_deadline) thì truyền allow_future=True."""
    absolute = parse_absolute_vietnamese(text)
    if absolute is not None:
        if not allow_future and absolute > reference_date:
            return None
        return absolute
    return parse_relative_vietnamese(text, reference_date)
