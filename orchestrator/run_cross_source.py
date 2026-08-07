"""
run_cross_source.py — Cross-Source Deduplication & Gold Layer Generator.

Chạy SAU khi tất cả per-source pipeline đã hoàn thành (đã có enriched.jsonl).
Đọc enriched.jsonl từ tất cả nguồn, dedupe chéo 1 lần, lưu gold layer thống nhất.

Cách dùng:
    python orchestrator/run_cross_source.py --date 2026-08-01
    python orchestrator/run_cross_source.py --date 2026-08-01 --skip-gold
"""
import argparse
import json
from pathlib import Path

from pipeline.model.job_posting import JobPosting
from pipeline.pipeline_steps.cross_source_dedupe import deduplicate
from pipeline.store.duckdb_store import store_to_gold

try:
    from shared.source_registry import SOURCE_REGISTRY
except ImportError:
    SOURCE_REGISTRY = {
        "itviec": {"skill_tag_structure": "flat"},
        "topcv": {"skill_tag_structure": "grouped"}
    }


def _read_enriched_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def main():
    arg_parser = argparse.ArgumentParser(description="Cross-source deduplication & gold layer generation")
    arg_parser.add_argument("--date", required=True, help="Ngày chạy batch (YYYY-MM-DD)")
    arg_parser.add_argument("--skip-gold", action="store_true", help="Bỏ qua bước lưu Gold Layer")
    args = arg_parser.parse_args()

    batch_date = args.date
    sources = list(SOURCE_REGISTRY.keys())
    all_enriched: list[dict] = []

    print(f"\n🚀 CROSS-SOURCE PIPELINE — NGÀY {batch_date}")
    print("-" * 60)

    print("[1/3] Đang đọc dữ liệu enriched từ tất cả nguồn...")
    for source in sources:
        enriched_file = Path(f"data/enriched/{source}/{batch_date}/enriched.jsonl")
        records = _read_enriched_jsonl(enriched_file)
        print(f"      - {source}: {len(records)} bản ghi")
        all_enriched.extend(records)

    if not all_enriched:
        print("⚠️ Không có dữ liệu enriched nào để xử lý.")
        return

    print(f"[2/3] Tổng cross-source: {len(all_enriched)} bản ghi")
    print("      Đang khử trùng lặp chéo nguồn...")

    enriched_models = []
    for rec in all_enriched:
        try:
            enriched_models.append(JobPosting(**rec))
        except Exception as e:
            print(f"      ❌ Lỗi parse JobPosting job_id={rec.get('job_id')}: {e}")

    if not enriched_models:
        print("⚠️ Không có bản ghi JobPosting hợp lệ nào.")
        return

    deduped_records = deduplicate(enriched_models)
    print(f"      -> Giảm từ {len(enriched_models)} xuống {len(deduped_records)} bản ghi duy nhất (Golden Records).")

    print("[3/3] Đang lưu trữ Gold Layer...")
    if not args.skip_gold:
        gold_path = store_to_gold(deduped_records, batch_date)
        if gold_path:
            print(f"      ✅ Đã lưu Gold Layer: {gold_path}")
    else:
        print("      ⏭️  Bỏ qua Gold Layer (--skip-gold).")

    print("-" * 60)
    print(f"🎉 HOÀN TẤT CROSS-SOURCE PIPELINE!")
    print(f"📊 Thống kê: Tổng {len(enriched_models)} -> Cross-dedupe: {len(deduped_records)}\n")


if __name__ == "__main__":
    main()
