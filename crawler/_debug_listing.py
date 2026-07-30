"""Debug script — kiểm tra listing spider output trước khi crawl detail.

Đọc jobs_meta_listing.jsonl, kiểm tra:
- Số lượng job_ids
- URL có hợp lệ không (không bị trống hoặc thiếu scheme)
- File raw_html listing đã tồn tại chưa
- Có trùng với jobs_meta_detail_status.jsonl không
"""
import json
import sys
from pathlib import Path


def debug_listing(batch_date: str):
    batch_dir = (
        Path(__file__).resolve().parent.parent.parent
        / "data"
        / "raw"
        / "itviec"
        / batch_date
    )

    listing_path = batch_dir / "jobs_meta_listing.jsonl"
    status_path = batch_dir / "jobs_meta_detail_status.jsonl"
    listing_html_dir = batch_dir / "raw_html" / "listing"

    if not listing_path.exists():
        print(f"ERROR: Không tìm thấy {listing_path}")
        return

    listing_jobs = []
    with open(listing_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                listing_jobs.append(row)
            except json.JSONDecodeError as e:
                print(f"WARN: JSON error: {e}")

    print(f"Listing jobs: {len(listing_jobs)}")

    # Check for bad URLs
    bad_urls = []
    for job in listing_jobs:
        url = job.get("url", "")
        job_id = job.get("job_id", "?")
        if not url:
            bad_urls.append((job_id, "empty URL"))
        elif not url.startswith("http"):
            bad_urls.append((job_id, f"bad scheme: {url[:80]}"))

    if bad_urls:
        print(f"Bad URLs ({len(bad_urls)}):")
        for jid, reason in bad_urls[:10]:
            print(f"  {jid}: {reason}")
    else:
        print("All URLs OK")

    # Check against detail status
    crawled_ids = set()
    if status_path.exists():
        with open(status_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    crawled_ids.add(row.get("job_id"))
                except json.JSONDecodeError:
                    continue

    not_crawled = [j for j in listing_jobs if j.get("job_id") not in crawled_ids]
    print(f"Already crawled (detail): {len(crawled_ids)}")
    print(f"Not yet crawled: {len(not_crawled)}")

    # Check listing HTML files
    missing_html = []
    for job in listing_jobs:
        job_id = job.get("job_id", "")
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(job_id))
        html_path = listing_html_dir / f"{safe_id}.html"
        if not html_path.exists():
            missing_html.append(job_id)

    if missing_html:
        print(f"Missing listing HTML ({len(missing_html)}):")
        for jid in missing_html[:5]:
            print(f"  {jid}")
    else:
        print(f"All {len(listing_jobs)} listing HTML files exist")

    # Sample first 3 jobs
    print("\nSample jobs:")
    for job in listing_jobs[:3]:
        print(f"  {job.get('job_id', '?')[:50]} | {job.get('title', '?')[:60]} | {job.get('url', '?')[:80]}")


if __name__ == "__main__":
    batch_date = sys.argv[1] if len(sys.argv) > 1 else "2026-07-28"
    debug_listing(batch_date)