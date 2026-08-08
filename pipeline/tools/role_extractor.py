"""
role_extractor.py — Chuẩn hóa vai trò công việc (canonical Job Role) từ tiêu đề.

Chỉ giữ `job_role` canonical (VD: data_engineer, data_analyst, data_scientist...)
để dashboard phân tích được theo trục vai trò. Title thô ("Senior Data Engineer",
"Chuyên viên Phân tích dữ liệu") được bóc tách thành 1 giá trị role chuẩn hóa.

Thiết kế:
- Keyword-based, có THỨ TỰ ƯU TIÊN (ưu tiên role cụ thể hơn trước role chung).
- Hỗ trợ cả tiếng Anh và tiếng Việt.
- Mở rộng dễ dàng: thêm role mới (VD data_analyst) chỉ cần thêm 1 entry vào
  _ROLE_PATTERNS — không phải sửa logic.
- Trả về canonical role snake_case, hoặc None nếu không nhận diện được.
"""
import re
from typing import Optional

# Bảng role canonical. Thứ tự duyệt theo mức độ SPECIFIC: role nào càng cụ thể
# (ít "nuốt" nhầm role khác) càng đặt trước. Mỗi role là list regex patterns.
# Lưu ý dùng \b để tránh khớp nhầm tiền tố (VD "data" trong "database", "analyst"
# trong "analytics").
_ROLE_PATTERNS: dict[str, list[str]] = {
    # ---- Data / Analytics ----
    "data_engineer": [
        r"\bdata\s+engineer\b",
        r"\bdata\s+integration\b",
        r"\bdata\s+infrastructure\b",
        r"\bdata\s+platform\b",
        r"\bdata\s+architect\b",
        r"\betl\s+(?:engineer|developer)\b",
        r"\betl\b",
        r"\bdata\s+systems\b",
        r"\bkỹ\s+sư\s+dữ\s+liệu\b",
        r"\bkỹ\s+thuật\s+dữ\s+liệu\b",
        r"\bbig\s+data\b",
        r"\bhead\s+of\s+data\b",
        r"\bdata\s+solution\b",
        r"\bgiải\s+cứu\s+dữ\s+liệu\b",
        r"\bchuyên\s+gia\s+(?:tích\s+hợp|dữ\s+liệu)\b",
        r"\bkỹ\s+sư\s+tích\s+hợp\s+dữ\s+liệu\b",
        r"\btrưởng\s+nhóm\s+dữ\s+liệu\b",
        r"\blead\s+data\s+engineer\b",
    ],
    "business_analyst": [
        r"\bbusiness\s+analyst\b",
        r"\bchuyên\s+viên\s+phân\s+tích\s+nghiệp\s+vụ\b",
    ],
    "data_analyst": [
        r"\bdata\s+analyst\b",
        r"\bbusiness\s+intelligence\s+analyst\b",
        r"\bbi\s+analyst\b",
        r"\bpower\s+bi\b",
        r"\bnghiên\s+cứu\s+dữ\s+liệu\b",
        r"\bchuyên\s+viên\s+phân\s+tích\s+dữ\s+liệu\b",
        r"\bphân\s+tích\s+dữ\s+liệu\b",
        r"\bdata\s+analytics\b",
        r"\banalytics\s+engineer\b",
        r"\bxử\s+lý\s+dữ\s+liệu\b",
        r"\bdata\s+intelligence\b",
        r"\bdata\s+specialist\b",
    ],
    "data_scientist": [
        r"\bdata\s+scientist\b",
        r"\bkhoa\s+học\s+dữ\s+liệu\b",
        r"\bchuyên\s+gia\s+khoa\s+học\s+dữ\s+liệu\b",
        r"\bdata\s+science\b",
    ],
    "ml_engineer": [
        r"\bmachine\s+learning\s+engineer\b",
        r"\bml\s+engineer\b",
        r"\bmlops\b",
        r"\bkỹ\s+sư\s+máy\s+học\b",
        r"\bdeep\s+learning\s+engineer\b",
    ],
    "ai_engineer": [
        r"\bai\s+engineer\b",
        r"\bai\s+developer\b",
        r"\bgenerative\s+ai\b",
        r"\bllm\s+engineer\b",
        r"\bai\s+ml\b",
        r"\bkỹ\s+sư\s+ai\b",
        r"\btrí\s+tuệ\s+nhân\s+tạo\b",
    ],
    "data_governance": [
        r"\bdata\s+governance\b",
        r"\bdata\s+quality\b",
        r"\bdata\s+management\b",
        r"\bchất\s+lượng\s+dữ\s+liệu\b",
        r"\bquản\s+trị\s+dữ\s+liệu\b",
    ],

    # ---- Software Engineering ----
    "backend_engineer": [
        r"\bbackend\b",
        r"\bback\s+end\b",
        r"\bapi\s+(?:developer|engineer)\b",
        r"\bserver\s+side\b",
        r"\blập\s+trình\s+viên\s+backend\b",
    ],
    "frontend_engineer": [
        r"\bfrontend\b",
        r"\bfront\s+end\b",
        r"\bweb\s+developer\b",
        r"\bui\s+developer\b",
        r"\blập\s+trình\s+viên\s+frontend\b",
    ],
    "fullstack_engineer": [
        r"\bfullstack\b",
        r"\bfull\s+stack\b",
        r"\blập\s+trình\s+viên\s+fullstack\b",
        r"\bweb\s+engineer\b",
    ],
    "devops_engineer": [
        r"\bdevops\b",
        r"\bsre\b",
        r"\bsite\s+reliability\b",
        r"\bplatform\s+engineer\b",
        r"\bcloud\s+engineer\b",
        r"\bci/cd\b",
        r"\bquản\s+trị\s+hệ\s+thống\b",
        r"\binfrastructure\b",
        r"\bit\s+server\b",
        r"\bdata\s+center\b",
    ],
    "qa_engineer": [
        r"\bqa\b",
        r"\bquality\s+assurance\b",
        r"\bqc\b",
        r"\btester\b",
        r"\bkiểm\s+thử\b",
        r"\bkiểm\s+chất\s+lượng\b",
    ],

    # ---- Generic software (fallback) ----
    "software_engineer": [
        r"\bsoftware\s+engineer\b",
        r"\bsoftware\s+developer\b",
        r"\bdeveloper\b",
        r"\bprogrammer\b",
        r"\blập\s+trình\s+(?:viên|phần\s+mềm)\b",
        r"\bkỹ\s+sư\s+phần\s+mềm\b",
        r"\bphát\s+triển\s+giải\s+pháp\b",
        r"\be-?\s*com\b",
    ],

    # ---- Management / Leadership (role-level, không phải chức vụ) ----
    "engineering_manager": [
        r"\bengineering\s+manager\b",
        r"\bhead\s+of\s+engineering\b",
        r"\btrưởng\s+phòng\s+kỹ\s+thuật\b",
        r"\btrưởng\s+nhóm\s+kỹ\s+thuật\b",
        r"\bgiám\s+đốc\s+công\s+nghệ\b",
        r"\bcto\b",
        r"\bmanager\b",
        r"\bquản\s+lý\b",
    ],
    "solution_architect": [
        r"\bsolution\s+architect\b",
        r"\bsolutions\s+architect\b",
        r"\bsoftware\s+architect\b",
        r"\bsystem\s+architect\b",
        r"\bkiến\s+trúc\s+sư\b",
        r"\bkiến\s+trúc\s+sư\s+công\s+nghệ\b",
    ],
    "product_manager": [
        r"\bproduct\s+manager\b",
        r"\bproduct\s+owner\b",
        r"\bquản\s+lý\s+sản\s+phẩm\b",
    ],
    "project_manager": [
        r"\bproject\s+manager\b",
        r"\bproject\s+coordinator\b",
        r"\bquản\s+lý\s+dự\s+án\b",
    ],
    "technical_writer": [
        r"\btechnical\s+writer\b",
    ],
    "support_engineer": [
        r"\bsupport\s+engineer\b",
        r"\bhelp\s+desk\b",
        r"\bysupport\b",
        r"\bhỗ\s+trợ\s+kỹ\s+thuật\b",
    ],
    "security_engineer": [
        r"\bsecurity\s+engineer\b",
        r"\bcybersecurity\b",
        r"\bpenetration\b",
        r"\bsecurity\s+analyst\b",
        r"\ban\s+toàn\s+thông\s+tin\b",
    ],
}

# Compile sẵn các pattern để tăng tốc.
_COMPILED: list[tuple[str, list[re.Pattern]]] = [
    (role, [re.compile(p, re.IGNORECASE) for p in patterns])
    for role, patterns in _ROLE_PATTERNS.items()
]


def _find_role(text: str) -> Optional[str]:
    """Tìm role canonical đầu tiên khớp trong text (theo thứ tự ưu tiên)."""
    if not text:
        return None
    for role, patterns in _COMPILED:
        for pattern in patterns:
            if pattern.search(text):
                return role
    return None


from pipeline.tools.vocab_gap_logger import log_unrecognized_role


def extract_role(title: str, requirements_text: Optional[str] = None, source: Optional[str] = None, job_id: Optional[str] = None) -> Optional[str]:
    """
    Chuẩn hóa vai trò công việc từ title (và tuỳ chọn requirements_text).

    Args:
        title: Tiêu đề công việc (VD: "Senior Data Engineer", "Chuyên viên phân tích dữ liệu").
        requirements_text: Text yêu cầu ứng viên (từ source_extra.requirements_raw) —
                           dùng làm fallback khi title không có tín hiệu.
        source: Nguồn gốc job (để log vocab gap).
        job_id: Định danh job (để log vocab gap).

    Returns:
        Một trong các canonical role (data_engineer, data_analyst, ...), hoặc None.
    """
    if title:
        role = _find_role(title)
        if role:
            return role

    # Fallback: nếu title không có tín hiệu, thử match requirements_text.
    if requirements_text:
        role = _find_role(requirements_text)
        if role:
            return role

    log_unrecognized_role(title, source=source or "unknown", job_id=job_id or "unknown")
    return None


def job_roles() -> list[str]:
    """Trả danh sách các role canonical hợp lệ (theo thứ tự ưu tiên)."""
    return list(_ROLE_PATTERNS.keys())
