"""
merge.py — điểm nối giữa crawler và pipeline.

Input: 2 file JSONL (Phase 1 + Phase 2) do crawler/job_crawler/pipelines.py ghi ra,
       + file .html riêng cho từng job (raw_html tách khỏi JSONL theo thiết kế đã chốt).
Output: list[RawRecord] — sẵn sàng cho sources/{source}/parse.py.

Join key = job_id (KHÔNG PHẢI url — url có query string tracking đổi mỗi lần crawl,
đã xác nhận trong crawler_design_final.md).
"""
import json
from pathlib import Path
from typing import Optional

from shared.utils import safe_id
from pipeline.model.raw_record import RawRecord


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # dòng hỏng — bỏ qua, không chặn cả batch
    return rows


def _read_html_if_exists(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def merge_raw_records(source: str, batch_date: str, data_root: Path = Path("data/raw")) -> list[RawRecord]:
    batch_dir = data_root / source / batch_date

    listing_rows = _read_jsonl(batch_dir / "jobs_meta_listing.jsonl")
    detail_rows = _read_jsonl(batch_dir / "jobs_meta_detail_status.jsonl")
    detail_by_id = {row["job_id"]: row for row in detail_rows if "job_id" in row}

    records: list[RawRecord] = []
    skipped = 0

    for row in listing_rows:
        job_id = row.get("job_id")
        if not job_id:
            skipped += 1
            continue

        safe_id = safe_id(job_id)
        listing_html_path = batch_dir / "raw_html" / "listing" / f"{safe_id}.html"
        detail_html_path = batch_dir / "raw_html" / "job_detail" / f"{safe_id}.html"

        detail_row = detail_by_id.get(job_id)
        detail_crawled = detail_row is not None

        records.append(RawRecord(
            job_id=job_id,
            source=source,
            batch_date=batch_date,
            url=row.get("url", ""),
            title_listing=row.get("title", ""),
            listing_page_num=row.get("listing_page_num"),
            listing_position=row.get("listing_position"),
            raw_html_listing=_read_html_if_exists(listing_html_path),
            detail_crawled=detail_crawled,
            title_detail=detail_row.get("title") if detail_row else None,
            raw_html_detail=_read_html_if_exists(detail_html_path) if detail_crawled else None,
        ))

    if skipped:
        print(f"[merge] {source}/{batch_date}: bỏ qua {skipped} dòng listing thiếu job_id")

    return records


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Dùng: python merge.py <source> <batch_date>")
        sys.exit(1)
    result = merge_raw_records(sys.argv[1], sys.argv[2])
    print(f"Merge xong: {len(result)} RawRecord, "
          f"{sum(1 for r in result if r.detail_crawled)} đã có detail.")
