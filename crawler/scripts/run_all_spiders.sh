#!/usr/bin/env bash
set -euo pipefail
BATCH_DATE=$(date -u +%Y-%m-%d)
cd "$(dirname "$0")/.."

scrapy crawl topcv_listing -a batch_date="$BATCH_DATE"
scrapy crawl topcv_detail  -a batch_date="$BATCH_DATE"
scrapy crawl itviec_listing -a batch_date="$BATCH_DATE"
scrapy crawl itviec_detail  -a batch_date="$BATCH_DATE"
