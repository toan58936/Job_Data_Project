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

[FIX P2 — elt_audit_report 2026-08-03]
- `locations` và `work_mode` trước đây KHÔNG được validate là required → giải
  thích tại sao 3.1% locations và 7.1% work_mode bị null. Thêm validate cho
  các field này, tuy nhiên chỉ flag chứ KHÔNG reject hoàn toàn (đánh dấu qua
  data_completeness = "partial" để không làm mất job vốn có description đầy đủ
  nhưng thiếu work_mode — rất phổ biến ở các job ít thông tin cấu trúc).

[Task 4] Validate posted_date:
- Nếu có posted_date, kiểm tra không phải quá khứ xa (>1 năm so với batch_date).
- Parser đã chặn tương lai (allow_future=False), nên không cần kiểm tra tương lai
  ở đây.
"""
import json
from datetime import date
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
        # [FIX P1] elt_audit_report: 4 job status=disclosed nhưng thiếu salary
        # min/max (itv_3847, itv_3902, tcv_8821, tcv_9014). Flag rõ ràng để
        # phát hiện sớm parser thiếu sót, thay vì để lọt vào Gold layer.
        if record.salary_min is None and record.salary_max is None:
            reasons.append("salary_disclosed_but_missing")

    # [Task 4] Validate posted_date: nếu có date thật, kiểm tra không phải quá khứ xa.
    # Parser đã chặn tương lai (allow_future=False), nên không cần kiểm tra tương lai.
    if record.posted_date is not None:
        try:
            batch = date.fromisoformat(record.batch_date)
            if (batch - record.posted_date).days > 365:
                reasons.append("posted_date_too_old")
        except ValueError:
            pass

    # [FIX P2] Validate locations/work_mode là required — NHƯNG KHÔNG reject.
    # lý do: elt_audit_report chỉ ra 3.1% locations và 7.1% work_mode rỗng,
    # đây là field quan trọng cho dashboard lọc theo tỉnh/thành và remote/hybrid.
    # Thay vì loại bỏ job (mất dữ liệu quý), hạ cấp data_completeness xuống
    # "incomplete" để dashboard biết mà lọc/cảnh báo.
    completeness_flags: list[str] = []
    if not record.locations:
        completeness_flags.append("missing_locations")
    if record.work_mode is None:
        completeness_flags.append("missing_work_mode")

    # data_completeness: suy từ description_raw rỗng hay không — KHÔNG dùng để
    # reject, chỉ để store/dashboard sau này lọc riêng nếu cần (job listing-only
    # thường thiếu mô tả đầy đủ, không nên trộn lẫn coi ngang hàng job đủ dữ liệu).
    if record.description_raw.strip():
        data_completeness = "full"
    elif completeness_flags:
        data_completeness = "incomplete"
    else:
        data_completeness = "listing_only"

    # Gắn cờ chi tiết trường thiếu vào source_extra để Enrich/lưu trữ dùng được
    record.source_extra["completeness_flags"] = completeness_flags

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
            # Bơm cờ phân loại vào kho mở rộng để trạm Enrich phía sau sử dụng
            record.source_extra["data_completeness"] = result.data_completeness
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