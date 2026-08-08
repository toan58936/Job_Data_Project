"""
seniority_extractor.py — Phân loại mức độ thâm niên (Seniority Level) từ tiêu đề
công việc và mô tả.

Trước đây `seniority_level` trong JobPosting luôn là None (shared_enrich.py hardcode
`seniority_level=None`), không có logic nào điền giá trị cho nó. Đây là gap chưa
được elt_audit_report 2026-08-03 đề cập (report chỉ tập trung P0/P1/P2 về skill,
salary, location, dedup). Module này lấp gap đó.

Thiết kế:
- Keyword-based, có THỨ TỰ ƯU TIÊN (cao → thấp) để xử lý title kết hợp như
  "Senior/Lead Data Engineer" (chọn mức cao nhất = senior), "Middle/Senior Data
  Engineer" (chọn middle/senior theo thứ tự ưu tiên).
- Hỗ trợ cả tiếng Anh và tiếng Việt.
- Fallback: nếu title không có tín hiệu rõ, dò description (theo tùy chọn).
- Trả về canonical: fresher | junior | middle | senior | lead | principal | expert | manager | director | staff
"""
import re
from typing import Optional

# Thứ tự ưu tiên TĂNG DẦN — mức càng cao càng "cao cấp" hơn. Khi title chứa nhiều
# từ khóa (vd "Senior/Lead"), ta chọn mức cao nhất (senior > lead > ...).
_SENIORITY_ORDER = [
    "fresher",
    "junior",
    "middle",
    "senior",
    "lead",
    "principal",
    "expert",
    "staff",
    "manager",
    "director",
]

# Regex cho từng mức. Lưu ý dùng \b để tránh khớp nhầm tiền tố (vd "senior" trong
# "seniority", "lead" trong "leadership"). Một số từ dùng lookahead để loại trừ
# ngữ cảnh không phải seniority (vd "technical lead" -> lead, nhưng "team lead" cũng lead).
_SENIORITY_PATTERNS: dict[str, list[str]] = {
    "fresher": [r"\bfresher\b", r"\bfreshers?\b", r"\bmới\s+tốt\s+nghiệp\b", r"\bthực\s+tập\b", r"\bintern\b", r"\binternship\b"],
    "junior": [r"\bjunior\b", r"\bjr\.?\b"],
    "middle": [r"\bmiddle\b", r"\bmid\b"],
    "senior": [r"\bsenior\b", r"\bsr\.?\b"],
    "lead": [r"\blead\b", r"\bleader\b", r"\btrưởng\s+nhóm\b", r"\btechnical\s+lead\b"],
    "principal": [r"\bprincipal\b", r"\bprinciple\b"],
    "expert": [r"\bexpert\b", r"\bchuyên\s+gia\b"],
    "staff": [r"\bstaff\b"],
    "manager": [r"\bmanager\b", r"\bmanagement\b", r"\bquản\s+lý\b", r"\btrưởng\s+phòng\b"],
    "director": [r"\bdirector\b", r"\bhead\s+of\b", r"\bgiám\s+đốc\b", r"\bvp\b", r"\bvice\s+president\b", r"\bcto\b", r"\bcfo\b", r"\bcoo\b"],
}

# Compile sẵn các pattern để tăng tốc.
_COMPILED: dict[str, list[re.Pattern]] = {
    level: [re.compile(p, re.IGNORECASE) for p in patterns]
    for level, patterns in _SENIORITY_PATTERNS.items()
}

# Một số title không có tín hiệu seniority nhưng vẫn là "manager" mang nghĩa quản lý
# kỹ thuật (không phải senior/kỹ thuật). Không cần đặc biệt vì "manager" đã có pattern.

# Các từ khóa "seniority" thường xuất hiện trong mô tả nhưng không phải tín hiệu
# mạnh (dễ false positive). Chỉ dùng description làm fallback khi title trống.
_USE_DESCRIPTION_FALLBACK = True


def _find_highest_level(text: str) -> Optional[str]:
    """Tìm mức seniority CAO NHẤT trong text dựa trên thứ tự ưu tiên."""
    if not text:
        return None
    # Duyệt từ mức cao nhất xuống thấp nhất — trả về mức đầu tiên khớp.
    for level in reversed(_SENIORITY_ORDER):
        for pattern in _COMPILED[level]:
            if pattern.search(text):
                return level
    return None


from pipeline.tools.vocab_gap_logger import log_unrecognized_role


def extract_seniority(title: str, description_raw: str = "", source: Optional[str] = None, job_id: Optional[str] = None) -> Optional[str]:
    """
    Phân loại seniority từ title (và tuỳ chọn description).

    Args:
        title: Tiêu đề công việc (VD: "Senior Data Engineer", "Chuyên gia tích hợp dữ liệu").
        description_raw: Mô tả công việc (dùng làm fallback khi title không có tín hiệu).

    Returns:
        Một trong các canonical: fresher | junior | middle | senior | lead | principal
        | expert | staff | manager | director, hoặc None nếu không nhận diện được.
    """
    if title:
        level = _find_highest_level(title)
        if level:
            return level

    # Fallback: nếu title không có tín hiệu, thử description (nếu được bật).
    if _USE_DESCRIPTION_FALLBACK and description_raw:
        level = _find_highest_level(description_raw)
        if level:
            return level

    log_unrecognized_role(title, source=source or "unknown", job_id=job_id or "unknown")
    return None


def seniority_levels() -> list[str]:
    """Trả danh sách các mức seniority hợp lệ (theo thứ tự ưu tiên tăng dần)."""
    return list(_SENIORITY_ORDER)
