#!/bin/bash
# run_all_spiders.ps1 — chạy tất cả spiders cho một batch date.
# Usage (PowerShell): pwsh -File run_all_spiders.ps1 -BatchDate 2026-07-28
# Usage (bash): bash run_all_spiders.sh 2026-07-28

BATCH_DATE="${1:-2026-07-28}"
CRAWLER_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Crawl Phase: Batch $BATCH_DATE ==="
echo ""

echo "[1/2] Crawling listings (itviec_listing + topcv_listing)..."
cd "$CRAWLER_DIR"
E:\job-data-project\.venv\Scripts\python.exe -m scrapy crawl itviec_listing -a batch_date="$BATCH_DATE" -s LOG_LEVEL=INFO
E:\job-data-project\.venv\Scripts\python.exe -m scrapy crawl topcv_listing -a batch_date="$BATCH_DATE" -s LOG_LEVEL=INFO

echo ""
echo "[2/2] Crawling details (itviec_detail + topcv_detail)..."
E:\job-data-project\.venv\Scripts\python.exe -m scrapy crawl itviec_detail -a batch_date="$BATCH_DATE" -s LOG_LEVEL=INFO
E:\job-data-project\.venv\Scripts\python.exe -m scrapy crawl topcv_detail -a batch_date="$BATCH_DATE" -s LOG_LEVEL=INFO

echo ""
echo "=== Crawl phase complete ==="