#!/bin/bash
# run_all_spiders.sh — chạy tất cả spiders cho một batch date.
# Usage: bash run_all_spiders.sh 2026-07-28

BATCH_DATE="${1:-2026-07-28}"
CRAWLER_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Crawl Phase: Batch $BATCH_DATE ==="
echo ""

echo "[1/2] Crawling listings..."
cd "$CRAWLER_DIR"
python -m scrapy crawl itviec_listing -a batch_date="$BATCH_DATE" -s LOG_LEVEL=INFO
python -m scrapy crawl topcv_listing -a batch_date="$BATCH_DATE" -s LOG_LEVEL=INFO

echo ""
echo "[2/2] Crawling details..."
python -m scrapy crawl itviec_detail -a batch_date="$BATCH_DATE" -s LOG_LEVEL=INFO
python -m scrapy crawl topcv_detail -a batch_date="$BATCH_DATE" -s LOG_LEVEL=INFO

echo ""
echo "=== Crawl phase complete ==="