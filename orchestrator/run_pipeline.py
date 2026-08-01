"""
run_pipeline.py — Nhạc trưởng điều phối toàn bộ luồng Data Pipeline.
Kết nối các module: Merge -> Parse -> Clean -> Normalize -> Salary Convert -> Validate -> Enrich.
Tự động lưu Checkpoint sau các chặng quan trọng (Normalized và Enriched).
"""
import argparse
import importlib
from pathlib import Path

from pipeline.pipeline_steps.merge import merge_raw_records
from pipeline.pipeline_steps.shared_clean import clean
from pipeline.pipeline_steps.shared_normalize import normalize
from pipeline.pipeline_steps.shared_salary_convert import convert_salary
from pipeline.pipeline_steps.shared_validate import validate_batch, write_rejected
from pipeline.pipeline_steps.shared_enrich import enrich
from shared.source_registry import SOURCE_REGISTRY


def load_parser(source: str):
    """Tự động nạp hàm parse.py tương ứng với nguồn (itviec, topcv)."""
    module = importlib.import_module(f"pipeline.sources.{source}.parse")
    return module


def main():
    parser = argparse.ArgumentParser(description="Chạy luồng xử lý Data Pipeline")
    parser.add_argument("--source", required=True, help="Tên nguồn (vd: itviec, topcv)")
    parser.add_argument("--date", required=True, help="Ngày chạy batch (YYYY-MM-DD)")
    args = parser.parse_args()

    source = args.source
    batch_date = args.date

    if source not in SOURCE_REGISTRY:
        print(f"❌ Lỗi: Nguồn '{source}' chưa được khai báo trong SOURCE_REGISTRY.")
        return

    print(f"\n🚀 BẮT ĐẦU CHẠY PIPELINE CHO {source.upper()} - NGÀY {batch_date}")
    print("-" * 60)

    # ==========================================
    # BƯỚC 1: MERGE DỮ LIỆU THÔ (Listing + Detail)
    # ==========================================
    print("[1/5] Đang merge dữ liệu thô từ Crawler...")
    raw_records = merge_raw_records(source, batch_date)
    if not raw_records:
        print("⚠️ Không có dữ liệu thô để xử lý. Dừng pipeline.")
        return
    print(f"      -> Tìm thấy {len(raw_records)} bản ghi.")

    # ==========================================
    # BƯỚC 2: PARSE -> CLEAN -> NORMALIZE -> SALARY
    # ==========================================
    print("[2/5] Đang Parse, Clean, Normalize và Quy đổi lương...")
    parse_module = load_parser(source)
    normalized_records = []
    
    for raw in raw_records:
        try:
            # Dòng chảy tuyến tính
            parsed = parse_module.parse(raw)
            cleaned = clean(parsed)
            normalized = normalize(cleaned)
            salary_converted = convert_salary(normalized)
            normalized_records.append(salary_converted)
        except Exception as e:
            print(f"      ❌ Lỗi xử lý job_id {raw.job_id}: {e}")

    # --- CHECKPOINT 1: LƯU DỮ LIỆU NORMALIZED ---
    normalized_dir = Path(f"data/normalized/{source}/{batch_date}")
    normalized_dir.mkdir(parents=True, exist_ok=True)
    normalized_file = normalized_dir / "normalized.jsonl"
    with open(normalized_file, "w", encoding="utf-8") as f:
        for rec in normalized_records:
            f.write(rec.model_dump_json() + "\n")
    print(f"      ✅ Đã lưu Checkpoint 1 (Normalized): {normalized_file}")

    # ==========================================
    # BƯỚC 3: KIỂM ĐỊNH CHẤT LƯỢNG (VALIDATE)
    # ==========================================
    print("[3/5] Đang kiểm định và lọc rác (Validate)...")
    registry_entry = SOURCE_REGISTRY[source]
    valid_records, rejected_records = validate_batch(normalized_records, registry_entry)
    
    if rejected_records:
        rej_file = write_rejected(rejected_records, source, batch_date)
        print(f"      🗑️ Đã loại bỏ {len(rejected_records)} bản ghi rác. Log tại: {rej_file}")
    else:
        print("      ✨ Không có bản ghi nào bị loại.")

    # ==========================================
    # BƯỚC 4: LÀM GIÀU DỮ LIỆU (ENRICH)
    # ==========================================
    print(f"[4/5] Đang Enrich {len(valid_records)} bản ghi hợp lệ thành JobPosting...")
    enriched_records = []
    for rec in valid_records:
        try:
            job_posting = enrich(rec)
            enriched_records.append(job_posting)
        except Exception as e:
            print(f"      ❌ Lỗi enrich job_id {rec.job_id}: {e}")

    # --- CHECKPOINT 2: LƯU DỮ LIỆU ENRICHED (GOLDEN SCHEMA) ---
    enriched_dir = Path(f"data/enriched/{source}/{batch_date}")
    enriched_dir.mkdir(parents=True, exist_ok=True)
    enriched_file = enriched_dir / "enriched.jsonl"
    with open(enriched_file, "w", encoding="utf-8") as f:
        for rec in enriched_records:
            f.write(rec.model_dump_json(exclude_none=True) + "\n")
    print(f"      ✅ Đã lưu Checkpoint 2 (Golden Data): {enriched_file}")

    # ==========================================
    # TỔNG KẾT
    # ==========================================
    print("-" * 60)
    print(f"🎉 HOÀN TẤT PIPELINE!")
    print(f"📊 Thống kê: Nhận {len(raw_records)} -> Hợp lệ {len(enriched_records)} -> Loại bỏ {len(rejected_records)}\n")


if __name__ == "__main__":
    main()