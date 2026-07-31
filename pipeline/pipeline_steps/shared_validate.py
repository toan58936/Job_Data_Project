"""
shared_validate.py — bước đầu tiên sau khi có SourceNormalized (parse.py xong).
Chặn rác sớm, trước khi tốn công clean/normalize/enrich cho dữ liệu sẽ bị vứt.

Rule dựa trên dữ liệu THẬT đã gặp trong quá trình build crawler/pipeline (không
phải suy đoán) — ví dụ job "finhay-0534" (ITviec, listing-only) từng có
company_name/locations rỗng trước khi sửa selector, minh hoạ đúng lý do cần
rule reject company_name_empty.

KHÔNG reject description_raw rỗng — case detail_crawled=False (listing-only)
có description_raw="" HỢP LỆ theo thiết kế (_parse_listing() luôn trả rỗng, có
chủ đích). Thay vào đó gắn cờ data_completeness để phân biệt, không loại bỏ.
"""
import json
from pathlib import Path
from typing import NamedTuple

from pipeline.model.source_normalized import SalaryStatus, SourceNormalized


class ValidationResult(NamedTuple):
    is_valid: bool
    reasons: list[str]              # rỗng nếu is_valid=True
    data_completeness: str          # "full" | "listing_only" — không ảnh hưởng is_valid


def validate(record: SourceNormalized, registry_entry: dict | None = None) -> ValidationResult:
    reasons: list[str] = []

    if not record.title.strip():
        reasons.append("title_empty")
    if not record.company_name.strip():
        reasons.append("company_name_empty")
    if not record.url.strip():
        reasons.append("url_empty")

    # salary_min/max chỉ có ý nghĩa kiểm tra khi salary_status=DISCLOSED — case
    # NEGOTIABLE/AUTH_GATED/NOT_PROVIDED đều hợp lệ có min/max=None, không phải lỗi.
    if record.salary_status == SalaryStatus.DISCLOSED:
        if (
            record.salary_min is not None
            and record.salary_max is not None
            and record.salary_min > record.salary_max
        ):
            reasons.append("salary_min_gt_max")

    # data_completeness: suy từ description_raw rỗng hay không — KHÔNG dùng để
    # reject, chỉ để store/dashboard sau này lọc riêng nếu cần (job listing-only
    # thường thiếu mô tả đầy đủ, không nên trộn lẫn coi ngang hàng job đủ dữ liệu).
    data_completeness = "full" if record.description_raw.strip() else "listing_only"

    return ValidationResult(
        is_valid=(len(reasons) == 0),
        reasons=reasons,
        data_completeness=data_completeness,
    )


def validate_batch(
    records: list[SourceNormalized],
    registry_entry: dict | None = None,
) -> tuple[list[SourceNormalized], list[dict]]:
    """Chạy validate() cho cả batch, tách 2 danh sách: job hợp lệ (đi tiếp) và
    job bị reject (kèm reason, ghi ra rejected.jsonl). Không tự ghi file ở đây —
    tách write_rejected() riêng để hàm này dễ test (không đụng filesystem)."""
    valid_records: list[SourceNormalized] = []
    rejected: list[dict] = []

    for record in records:
        result = validate(record, registry_entry)
        if result.is_valid:
            valid_records.append(record)
        else:
            rejected.append({
                "job_id": record.job_id,
                "source": record.source,
                "url": record.url,
                "reasons": result.reasons,
            })

    return valid_records, rejected


def write_rejected(rejected: list[dict], source: str, batch_date: str, data_root: Path = Path("data/rejected")) -> Path:
    """Ghi job bị reject ra data/rejected/{source}/{batch_date}/rejected.jsonl —
    append-only, đúng nguyên tắc "dữ liệu có vòng đời" đã chốt từ v1, không ghi
    đè để giữ lại lịch sử reject qua nhiều lần chạy."""
    out_dir = data_root / source / batch_date
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "rejected.jsonl"
    with open(out_path, "a", encoding="utf-8") as f:
        for row in rejected:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return out_path


if __name__ == "__main__":
    import sys
    print("shared_validate.py chạy độc lập cần list[SourceNormalized] có sẵn — "
          "dùng qua orchestrator hoặc import trực tiếp, không có CLI entrypoint riêng.")
    sys.exit(0)