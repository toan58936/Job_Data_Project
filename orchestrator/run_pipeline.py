"""
run_pipeline.py — Nhạc trưởng điều phối luồng Data Pipeline cho 1 nguồn.
Per-source: Merge -> Parse -> Clean -> Normalize -> Salary Convert -> Validate -> Enrich -> Dedupe -> Parquet.
Gold layer chỉ được tạo bởi cross-source pipeline (orchestrator/run_cross_source.py).
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
from pipeline.pipeline_steps.cross_source_dedupe import deduplicate
from pipeline.store.duckdb_store import store_to_parquet

try:
    from shared.source_registry import SOURCE_REGISTRY
except ImportError:
    SOURCE_REGISTRY = {
        "itviec": {"skill_tag_structure": "flat"},
        "topcv": {"skill_tag_structure": "grouped"}
    }


def load_parser(source: str):
    """Tự động nạp hàm parse.py tương ứng với nguồn (itviec, topcv)."""
    module = importlib.import_module(f"pipeline.sources.{source}.parse")
    return module


def run_per_source(source: str, batch_date: str):
    print(f"\n🚀 BẮT ĐẦU CHẠY PIPELINE CHO {source.upper()} - NGÀY {batch_date}")
    print("-" * 60)

    print("[1/6] Đang merge dữ liệu thô từ Crawler...")
    raw_records = merge_raw_records(source, batch_date)
    if not raw_records:
        print("⚠️ Không có dữ liệu thô để xử lý. Kiểm tra lại thư mục data/raw/")
        return
    print(f"      -> Tìm thấy {len(raw_records)} bản ghi (RawRecord).")

    print("[2/6] Đang Parse, Clean, Normalize và Quy đổi lương...")
    parse_module = load_parser(source)
    normalized_records = []
    for raw in raw_records:
        try:
            parsed = parse_module.parse(raw)
            cleaned = clean(parsed)
            normalized = normalize(cleaned)
            salary_converted = convert_salary(normalized)
            normalized_records.append(salary_converted)
        except Exception as e:
            print(f"      ❌ Lỗi xử lý job_id {raw.job_id}: {e}")

    normalized_dir = Path(f"data/normalized/{source}/{batch_date}")
    normalized_dir.mkdir(parents=True, exist_ok=True)
    normalized_file = normalized_dir / "normalized.jsonl"
    with open(normalized_file, "w", encoding="utf-8") as f:
        for rec in normalized_records:
            f.write(rec.model_dump_json() + "\n")
    print(f"      ✅ Đã lưu Checkpoint 1 (Normalized): {normalized_file}")

    print("[3/6] Đang kiểm định và lọc rác (Validate)...")
    registry_entry = SOURCE_REGISTRY[source]
    valid_records, rejected_records = validate_batch(normalized_records, registry_entry)
    if rejected_records:
        rej_file = write_rejected(rejected_records, source, batch_date)
        print(f"      🗑️ Đã loại bỏ {len(rejected_records)} bản ghi lỗi. Log tại: {rej_file}")
    else:
        print("      ✨ 100% bản ghi vượt qua kiểm định.")

    print("[4/6] Đang Enrich các bản ghi hợp lệ thành JobPosting...")
    enriched_records = []
    for rec in valid_records:
        try:
            job_posting = enrich(rec)
            enriched_records.append(job_posting)
        except Exception as e:
            print(f"      ❌ Lỗi enrich job_id {rec.job_id}: {e}")

    enriched_dir = Path(f"data/enriched/{source}/{batch_date}")
    enriched_dir.mkdir(parents=True, exist_ok=True)
    enriched_file = enriched_dir / "enriched.jsonl"
    with open(enriched_file, "w", encoding="utf-8") as f:
        for rec in enriched_records:
            f.write(rec.model_dump_json(exclude_none=True) + "\n")
    print(f"      ✅ Đã lưu Checkpoint 2 (Enriched): {enriched_file}")

    print("[5/6] Đang khử trùng lặp nội bộ nguồn (Deduplication)...")
    deduped_records = deduplicate(enriched_records)
    print(f"      -> Giảm từ {len(enriched_records)} xuống {len(deduped_records)} bản ghi duy nhất.")

    print("[6/6] Đang lưu trữ vào Parquet...")
    parquet_path = store_to_parquet(deduped_records, batch_date)
    if parquet_path:
        print(f"      ✅ Đã lưu Parquet: {parquet_path}")

    print("-" * 60)
    print(f"🎉 HOÀN TẤT PIPELINE CHO {source.upper()}!")
    print(f"📊 Thống kê: Nhận {len(raw_records)} -> Hợp lệ & Enriched: {len(enriched_records)} -> Sau dedupe: {len(deduped_records)} -> Loại bỏ: {len(rejected_records)}")
    print(f"💡 Gold layer sẽ được tạo bởi orchestrator/run_cross_source.py sau khi tất cả nguồn hoàn thành.\n")


def main():
    arg_parser = argparse.ArgumentParser(description="Chạy luồng xử lý Data Pipeline cho 1 nguồn")
    arg_parser.add_argument("--source", required=True, help="Tên nguồn (vd: itviec, topcv)")
    arg_parser.add_argument("--date", required=True, help="Ngày chạy batch (YYYY-MM-DD)")
    args = arg_parser.parse_args()

    source = args.source
    batch_date = args.date

    if source not in SOURCE_REGISTRY:
        print(f"❌ Lỗi: Nguồn '{source}' chưa được cấu hình.")
        return

    run_per_source(source, batch_date)


if __name__ == "__main__":
    main()
