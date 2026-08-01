"""
shared_clean.py — Bước 2: Làm sạch văn bản.
Nhiệm vụ: Loại bỏ ký tự Unicode vô hình, gom khoảng trắng thừa,
chuẩn hóa hệ thống gạch đầu dòng (bullet points), VÀ [MỚI] phát hiện/cắt
text bị lặp đôi do site render 2 khối trùng nội dung cho breakpoint
mobile/desktop (đã phát hiện ở cả 2 nguồn — ITviec: company_name lặp
"ITviec Recruitment Consulting ITviec Recruitment Consulting"; TopCV:
.tag/.tag-quickview chứa y hệt nội dung). Đây là lý do file này được tạo
ra ban đầu nhưng bản trước chưa có logic này — chỉ có whitespace/bullet.
"""
import re
from typing import Optional

from pipeline.model.source_normalized import SourceNormalized


def dedupe_repeated_block(text: str) -> str:
    """Nếu `text` là 2 bản sao dính liền của cùng 1 nội dung (cách nhau bởi
    khoảng trắng), cắt còn 1 bản. Không dùng cắt-nửa-chuỗi ngây thơ (dễ vỡ nếu
    2 nửa lệch whitespace) — so sánh sau khi chuẩn hoá khoảng trắng ở cả 2 nửa
    trước khi kết luận có trùng hay không.

    Chỉ xử lý trường hợp lặp đúng 2 lần dính liền (case thực tế đã gặp) — nếu
    lặp kiểu khác (rải rác, không liền kề) không đụng vào, để tránh cắt nhầm
    nội dung hợp lệ có 2 câu giống nhau ngẫu nhiên.
    """
    if not text:
        return text

    normalized = re.sub(r"\s+", " ", text).strip()
    length = len(normalized)
    if length < 4 or length % 2 != 0:
        # Độ dài lẻ không thể là 2 nửa bằng nhau dính liền — bỏ qua an toàn.
        return text

    half = length // 2
    first_half = normalized[:half].strip()
    second_half = normalized[half:].strip()

    if first_half and first_half == second_half:
        return first_half

    return text


def clean_text(text: Optional[str]) -> str:
    """
    Hàm tiện ích làm sạch một chuỗi văn bản thô.
    """
    if not text:
        return ""

    # 1. Quy chuẩn ngắt dòng (chuẩn hóa \r\n hoặc \r về \n)
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # 2. Tiêu diệt ký tự Unicode vô hình (non-breaking space, zero-width space) và tab
    text = re.sub(r'[\xa0\u200b\t]', ' ', text)

    # 3. Chuẩn hóa Bullet Points
    text = re.sub(r'^[ \t]*[•▪➢✓*+oO-][ \t]+', '- ', text, flags=re.MULTILINE)

    # 4. Gom khoảng trắng thừa (2 dấu cách trở lên -> 1 dấu cách)
    text = re.sub(r'[ \t]{2,}', ' ', text)

    # 5. Dọn dẹp dòng trống (từ 3 dấu xuống dòng liên tiếp trở lên -> giữ lại 2)
    text = re.sub(r'\n{3,}', '\n\n', text)

    text = text.strip()

    # 6. [MỚI] Cắt bỏ nếu toàn bộ chuỗi là 2 bản sao dính liền — áp dụng SAU khi
    # đã gom whitespace ở bước 4, để dedupe_repeated_block() so sánh chính xác.
    text = dedupe_repeated_block(text)

    return text


def clean(record: SourceNormalized) -> SourceNormalized:
    """
    Nhận vào bản ghi SourceNormalized, làm sạch các trường văn bản
    và trả về chính bản ghi đó.
    """
    # 1. Làm sạch mô tả cốt lõi
    record.description_raw = clean_text(record.description_raw)

    # 2. Làm sạch các trường văn bản mở rộng (thường xuất hiện ở TopCV)
    extra_text_fields = ["requirements_raw", "benefits_raw", "experience_raw"]
    for field in extra_text_fields:
        if field in record.source_extra and isinstance(record.source_extra[field], str):
            record.source_extra[field] = clean_text(record.source_extra[field])

    # 3. Dọn rác cơ bản cho Tiêu đề và Tên công ty (loại bỏ khoảng trắng thừa
    # VÀ text lặp đôi — đây chính là field từng gặp bug "ITviec Recruitment
    # Consulting ITviec Recruitment Consulting" khi debug parse.py trước đây).
    record.title = clean_text(record.title)
    record.company_name = clean_text(record.company_name)

    return record
