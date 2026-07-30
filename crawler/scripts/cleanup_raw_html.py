"""Retention cleanup — removes raw HTML files older than retention_days
from data/raw/{source}/{batch_date}/raw_html/job_detail/ (and listing/).

Keeps the N most recent batches per source (default 3).
Safe to run repeatedly (no-op on missing files).
"""
import argparse
from datetime import datetime, timedelta
from pathlib import Path


def cleanup_raw_html(
    raw_root: Path,
    retention_days: int = 30,
    dry_run: bool = False,
):
    cutoff = datetime.now() - timedelta(days=retention_days)
    deleted = 0
    kept = 0
    errors = 0

    for source_dir in sorted(raw_root.iterdir()):
        if not source_dir.is_dir():
            continue
        for batch_dir in sorted(source_dir.iterdir()):
            if not batch_dir.is_dir():
                continue
            html_dir = batch_dir / "raw_html"
            if not html_dir.exists():
                continue
            for kind_dir in sorted(html_dir.iterdir()):
                if not kind_dir.is_dir():
                    continue
                for html_file in sorted(kind_dir.iterdir()):
                    if not html_file.is_file():
                        continue
                    mtime = datetime.fromtimestamp(html_file.stat().st_mtime)
                    if mtime < cutoff:
                        if not dry_run:
                            try:
                                html_file.unlink()
                                deleted += 1
                            except OSError as exc:
                                print(f"  ERROR deleting {html_file}: {exc}")
                                errors += 1
                        else:
                            kept += 1
                    else:
                        kept += 1

    label = "[DRY RUN]" if dry_run else "[DELETE]"
    print(
        f"{label} Retention cleanup (>{retention_days}d): "
        f"kept={kept}, deleted={deleted}, errors={errors}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Clean up old raw HTML files from crawler output"
    )
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent.parent / "data" / "raw",
        help="Root of data/raw/ directory (default: project root)",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=30,
        help="Delete files older than this many days (default: 30)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List what would be deleted without actually deleting",
    )
    args = parser.parse_args()

    cleanup_raw_html(args.raw_root, args.retention_days, args.dry_run)