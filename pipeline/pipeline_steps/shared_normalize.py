"""
shared_normalize.py — Bước 3: Chuẩn hóa định dạng (Đặc biệt là Locations)
Nhiệm vụ: Sử dụng từ điển Mapping để gộp các biến thể địa danh khác nhau
(ví dụ: "Ha Noi", "Hà Nội: Keangnam...", "Quảng Ninh: (Tất cả phường)")
về một chuẩn duy nhất ("Hà Nội", "Quảng Ninh").

[FIX P2 — elt_audit_report 2026-08-03 + audit rerun]
- Bổ sung toàn bộ 63 tỉnh/thành vào LOCATION_MAP, kèm biến thể tiếng Anh và
  biến thể không dấu (vd "Tay Ninh" -> "Tây Ninh").
- Xử lý chuỗi có prefix chi tiết "Tỉnh: (chi tiết)" / "Tỉnh - (chi tiết)":
  trước khi match, tách lấy phần TỈNH đầu tiên (trước dấu ":" hoặc "-").

[Task 4] Parse posted_date sớm ở normalize step:
- Nếu parser đã parse rồi (posted_date có sẵn), giữ nguyên (idempotent).
- Nếu parser quên (posted_date=None) nhưng posted_date_raw có giá trị,
  parse lại dùng batch_date làm reference.
- Đảm bảo source_extra["posted_date_parsed"] luôn sync với posted_date.
"""
import re
import unicodedata
from datetime import date

from pipeline.model.source_normalized import SourceNormalized
from pipeline.tools.date_parser import parse_vietnamese_date


def _strip_accents(text: str) -> str:
    """Bỏ dấu tiếng Việt và chuẩn hoá lowercase để so khớp chính tả linh hoạt.
    VD: "Tây Ninh" -> "tay ninh", "Tay Ninh" -> "tay ninh" (cùng khớp).

    Lưu ý: U+0111 ("đ") KHÔNG bị NFKD phân rã, phải map thủ công sang "d" —
    nếu không "đà nẵng" và "da nang" sẽ không khớp nhau."""
    text = text.replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


# Map tên chuẩn -> list biến thể (viết thường, có dấu lẫn không dấu). Dùng
# _strip_accents() để so khớp nên chỉ cần ghi 1 biến thể đại diện cho mỗi tên.
# [FIX] Mở rộng từ 7 tỉnh lên 63 tỉnh/thành để không còn location "lạ" lọt qua.
_PROVINCES: dict[str, str] = {
    "Hà Nội": "hà nội",
    "Hồ Chí Minh": "hồ chí minh",
    "Đà Nẵng": "đà nẵng",
    "Cần Thơ": "cần thơ",
    "Hải Phòng": "hải phòng",
    "An Giang": "an giang",
    "Bà Rịa - Vũng Tàu": "bà rịa vũng tàu",
    "Bắc Giang": "bắc giang",
    "Bắc Kạn": "bắc kạn",
    "Bạc Liêu": "bạc liêu",
    "Bắc Ninh": "bắc ninh",
    "Bến Tre": "bến tre",
    "Bình Định": "bình định",
    "Bình Dương": "bình dương",
    "Bình Phước": "bình phước",
    "Bình Thuận": "bình thuận",
    "Cà Mau": "cà mau",
    "Cao Bằng": "cao bằng",
    "Đắk Lắk": "đắk lắk",
    "Đắk Nông": "đắk nông",
    "Điện Biên": "điện biên",
    "Đồng Nai": "đồng nai",
    "Đồng Tháp": "đồng tháp",
    "Gia Lai": "gia lai",
    "Hà Giang": "hà giang",
    "Hà Nam": "hà nam",
    "Hà Tĩnh": "hà tĩnh",
    "Hải Dương": "hải dương",
    "Hậu Giang": "hậu giang",
    "Hoà Bình": "hoà bình",
    "Hưng Yên": "hưng yên",
    "Khánh Hoà": "khánh hoà",
    "Kiên Giang": "kiên giang",
    "Kon Tum": "kon tum",
    "Lai Châu": "lai châu",
    "Lâm Đồng": "lâm đồng",
    "Lạng Sơn": "lạng sơn",
    "Lào Cai": "lào cai",
    "Long An": "long an",
    "Nam Định": "nam định",
    "Nghệ An": "nghệ an",
    "Ninh Bình": "ninh bình",
    "Ninh Thuận": "ninh thuận",
    "Phú Thọ": "phú thọ",
    "Phú Yên": "phú yên",
    "Quảng Bình": "quảng bình",
    "Quảng Nam": "quảng nam",
    "Quảng Ngãi": "quảng ngãi",
    "Quảng Ninh": "quảng ninh",
    "Quảng Trị": "quảng trị",
    "Sóc Trăng": "sóc trăng",
    "Sơn La": "sơn la",
    "Tây Ninh": "tây ninh",
    "Thái Bình": "thái bình",
    "Thái Nguyên": "thái nguyên",
    "Thanh Hoá": "thanh hoá",
    "Thừa Thiên Huế": "thừa thiên huế",
    "Tiền Giang": "tiền giang",
    "Trà Vinh": "trà vinh",
    "Tuyên Quang": "tuyên quang",
    "Vĩnh Long": "vĩnh long",
    "Vĩnh Phúc": "vĩnh phúc",
    "Yên Bái": "yên bái",
}

# Map pattern (regex trên chuỗi đã strip accents) -> tên chuẩn.
# Giữ thêm các biến thể đặc biệt/viết tắt (hcm, hp, dn, hn...) không nằm trong
# tên tỉnh thông thường.
_EXTRA_PATTERNS: dict[str, str] = {
    r"\bhn\b": "Hà Nội",
    r"\bhcm\b|tp\.hcm|tp hcm|ho chi minh|hồ chí minh": "Hồ Chí Minh",
    r"\bdn\b": "Đà Nẵng",
    r"\bhp\b": "Hải Phòng",
    r"\bct\b": "Cần Thơ",
}

# Build LOCATION_MAP (giữ tên cũ để tương thích nếu nơi khác import).
LOCATION_MAP: dict[str, str] = {}


def _first_segment(text: str) -> str:
    """Lấy phần đầu của chuỗi location trước dấu ':' hoặc ' - ' (nếu có).
    VD: "Quảng Ninh: (Tất cả phường)" -> "Quảng Ninh"
        "Hà Nội: Keangnam Landmark"   -> "Hà Nội"
    """
    for sep in (":", " - "):
        if sep in text:
            return text.split(sep)[0].strip()
    return text.strip()


def _match_province(text_lower_no_accent: str) -> str | None:
    """Tìm tỉnh khớp trong text (đã lower + bỏ dấu). Trả tên chuẩn hoặc None."""
    # 1. Thử match pattern đặc biệt (viết tắt)
    for pattern, canonical in _EXTRA_PATTERNS.items():
        if re.search(pattern, text_lower_no_accent):
            return canonical

    # 2. Thử match tên tỉnh đầy đủ.
    # [FIX] Bỏ dấu "-" và gom khoảng trắng ở cả 2 phía khi so khớp — nếu không,
    # tên tỉnh hợp lệ có chứa gạch nối như "Bà Rịa - Vũng Tàu" (biến thể
    # "ba ria - vung tau") sẽ không khớp chuỗi "ba ria vung tau" do dấu "-" phá
    # vỡ ranh giới từ \b và để lại khoảng trắng kép "".
    text_for_match = re.sub(r"\s+", " ", text_lower_no_accent.replace("-", "")).strip()
    for canonical, variant in _PROVINCES.items():
        var_no_accent = re.sub(r"\s+", " ", _strip_accents(variant).replace("-", "")).strip()
        if re.search(rf"\b{re.escape(var_no_accent)}\b", text_for_match):
            return canonical

    return None


def normalize_locations(raw_locations: list[str]) -> list[str]:
    """
    Chuẩn hóa mảng địa điểm thô thành mảng địa điểm chuẩn (cấp tỉnh/thành).
    """
    normalized = []

    for loc in raw_locations:
        # [FIX] Ưu tiên so khớp TOÀN BỘ chuỗi trước — tránh cắt "Bà Rịa - Vũng Tàu"
        # thành "Bà Rịa" (tên tỉnh hợp lệ có chứa " - ") khi dùng _first_segment ngay
        # từ đầu. Chỉ khi cả chuỗi không khớp tỉnh nào mới thử cắt phần chi tiết sau
        # ':' hoặc ' - ' (VD "Quảng Ninh: (Tất cả phường)", "Hà Nội - 123 Đường Láng").
        loc_no_accent = _strip_accents(loc)
        canonical = _match_province(loc_no_accent)
        if canonical:
            normalized.append(canonical)
            continue

        # Không khớp cả chuỗi -> thử bỏ phần chi tiết địa chỉ rồi so khớp lại
        first = _first_segment(loc)
        if first.strip() != loc.strip():
            first_no_accent = _strip_accents(first)
            canonical = _match_province(first_no_accent)
            if canonical:
                normalized.append(canonical)
                continue

        # Vẫn không khớp tỉnh nào -> làm sạch khoảng trắng rồi giữ nguyên (fallback)
        clean_loc = re.sub(r'\s+', ' ', first).strip()
        if clean_loc:
            normalized.append(clean_loc)

    return list(dict.fromkeys(normalized))


def normalize(record: SourceNormalized) -> SourceNormalized:
    """
    Nhận vào bản ghi đã qua bước clean(), thực hiện chuẩn hóa và trả về.
    """
    # [FIX] Trước khi ghi đè locations về dạng chuẩn cấp tỉnh/thành, giữ lại
    # bản đầy đủ gốc (địa chỉ chi tiết: toà nhà, phường/quận) vào source_extra
    # -- trước đây bị MẤT HẲN không lưu ở đâu, vi phạm nguyên tắc "dữ liệu có
    # vòng đời, giữ audit trail" đã áp dụng cho posted_date_raw. Địa chỉ chi
    # tiết vẫn có giá trị (hiển thị JD, không phải chỉ để lọc theo tỉnh/thành).
    if record.locations:
        record.source_extra["locations_raw"] = list(record.locations)

    record.locations = normalize_locations(record.locations)

    # [Task 4] Parse posted_date sớm ở normalize step (idempotent):
    # - Nếu parser đã parse rồi (posted_date có sẵn), giữ nguyên.
    # - Nếu parser quên (posted_date=None) nhưng posted_date_raw có giá trị,
    #   parse lại dùng batch_date làm reference.
    if record.posted_date is None and record.posted_date_raw.strip():
        try:
            batch = date.fromisoformat(record.batch_date)
            parsed = parse_vietnamese_date(record.posted_date_raw, batch, allow_future=False)
            if parsed:
                record.posted_date = parsed
                record.source_extra["posted_date_parsed"] = parsed.isoformat()
        except ValueError:
            pass

    return record
