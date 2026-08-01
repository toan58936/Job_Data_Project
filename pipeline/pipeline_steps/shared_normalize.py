"""
shared_normalize.py — Bước 3: Chuẩn hóa định dạng (Đặc biệt là Locations)
Nhiệm vụ: Sử dụng từ điển Mapping để gộp các biến thể địa danh khác nhau
(ví dụ: "Ha Noi", "Hà Nội: Keangnam...") về một chuẩn duy nhất ("Hà Nội").
"""
import re

from pipeline.model.source_normalized import SourceNormalized

# [FIX] Bọc \b (word boundary) quanh viết tắt ngắn ("hn", "hcm") — trước đây
# dùng substring trần, có nguy cơ khớp nhầm bất kỳ chuỗi nào chứa "hn"/"hcm"
# như 1 đoạn con của từ khác. Tên đầy đủ ("hà nội", "hồ chí minh"...) giữ
# nguyên không cần \b vì đủ dài để không lo trùng ngẫu nhiên.
LOCATION_MAP = {
    r"hà nội|ha noi|\bhn\b": "Hà Nội",
    r"hồ chí minh|ho chi minh|\bhcm\b|tp\.hcm|tp hcm": "Hồ Chí Minh",
    r"đà nẵng|da nang": "Đà Nẵng",
    r"cần thơ|can tho": "Cần Thơ",
    r"hải phòng|hai phong": "Hải Phòng",
    r"bình dương|binh duong": "Bình Dương",
    r"đồng nai|dong nai": "Đồng Nai",
}


def normalize_locations(raw_locations: list[str]) -> list[str]:
    """
    Chuẩn hóa mảng địa điểm thô thành mảng địa điểm chuẩn (cấp tỉnh/thành).
    """
    normalized = []

    for loc in raw_locations:
        loc_lower = loc.lower()
        matched = False

        for pattern, canonical in LOCATION_MAP.items():
            if re.search(pattern, loc_lower):
                normalized.append(canonical)
                matched = True
                break

        if not matched:
            clean_loc = re.sub(r'\s+', ' ', loc).strip()
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

    return record