# 🏗️ Job Data ELT Pipeline

Hệ thống **ETL pipeline** thu thập và xử lý dữ liệu tuyển dụng IT từ 2 nguồn **ITviec** và **TopCV** theo kiến trúc 4 tầng:

```
Bronze (raw) → Silver (normalized/enriched) → Gold (clean parquet)
```

> **Pipeline**: Crawler (Scrapy + Playwright) → Parse → Clean → Normalize → Salary Convert → Validate → Enrich → Dedup → Gold Layer (Parquet/Data Lake)

---

## 📁 Cấu trúc thư mục

```
job-data-project/
├── crawler/                 # Scrapy crawler (Listing + Detail spiders)
│   ├── job_crawler/
│   │   ├── spiders/         # itviec_*, topcv_* spiders
│   │   ├── settings.py      # Playwright, cookie, anti-bot
│   │   ├── middlewares.py   # Rotating UA, Login, ForcePlaywright
│   │   └── pipelines.py     # JSONL writer
│   └── scripts/             # run_all_spiders, login_itviec, cleanup
├── pipeline/
│   ├── sources/             # itviec/parse.py, topcv/parse.py
│   ├── pipeline_steps/      # clean, normalize, salary_convert, validate, enrich, dedupe
│   ├── config/              # skills_taxonomy.py
│   ├── model/               # RawRecord, SourceNormalized, JobPosting
│   ├── tools/               # skill_extractor, date_parser, vocab_gap_logger
│   ├── store/               # duckdb_store.py (parquet writer)
│   └── tests/               # unit tests
├── orchestrator/run_pipeline.py  # CLI pipeline runner
├── data/                    # raw / normalized / enriched / clean / rejected / metadata
├── docs/                    # Tài liệu kiến trúc + HTML sample
└── shared/                  # source_registry, utils
```

---

## ⚙️ Yêu cầu hệ thống

- **Python 3.10+** (Playwright yêu cầu tương thích)
- **Windows / Linux / macOS**
- Kết nối internet (để crawl + tải Playwright browser)

---

## 🚀 Cài đặt (Setup)

### 1. Clone dự án & tạo môi trường ảo

```bash
# Linux/macOS
cd job-data-project
python3 -m venv .venv
source .venv/bin/activate

# Windows
cd job-data-project
python -m venv .venv
.venv\Scripts\activate
```

### 2. Cài đặt các dependency

```bash
# Cài dependency cho CRAWLER (Scrapy + Playwright)
pip install -r crawler/requirements.txt

# Cài dependency cho PIPELINE (xử lý dữ liệu)
pip install pandas pyarrow duckdb pydantic flashtext lxml python-dotenv requests
```

> Nếu bạn có file `requirements.txt` ở gốc dự án, có thể chạy `pip install -r requirements.txt` (nếu chưa có thì tạo từ danh sách trên).

### 3. Cài Playwright browser (Chromium)

```bash
# Cài browser Chromium để Scrapy-Playwright render trang
playwright install chromium
```

### 4. Cấu hình biến môi trường (`.env`)

Tạo file `.env` ở **gốc dự án** (đã có sẵn `.env` trong repo):

```env
# Thông tin đăng nhập ITviec (dùng để crawl lương đầy đủ, tránh AUTH_GATED)
ITVIEC_EMAIL=your_email@example.com
ITVIEC_PASSWORD=your_password
```

---

## 🕷️ Chạy Crawler (Extract — Bronze layer)

### Chạy toàn bộ (listing + detail, cả 2 nguồn)

```bash
# Windows (PowerShell) — mặc định dùng ngày hôm nay
.\crawler\scripts\run_all_spiders.ps1

# Chỉ định batch date cụ thể
.\crawler\scripts\run_all_spiders.ps1 -BatchDate "2026-08-01"

# Linux/macOS
bash crawler/scripts/run_all_spiders.sh
```

### Chạy thủ công từng spider

```bash
# Từ thư mục crawler/
cd crawler

# Crawl listing
python -m scrapy crawl itviec_listing -a batch_date="2026-08-01" -s LOG_LEVEL=INFO
python -m scrapy crawl topcv_listing -a batch_date="2026-08-01" -s LOG_LEVEL=INFO

# Crawl detail
python -m scrapy crawl itviec_detail -a batch_date="2026-08-01" -s LOG_LEVEL=INFO
python -m scrapy crawl topcv_detail -a batch_date="2026-08-01" -s LOG_LEVEL=INFO
```

**Output**: `data/raw/{source}/{batch_date}/jobs_meta_listing.jsonl` + `jobs_meta_detail_status.jsonl` + `raw_html/`

### 🔑 Đăng nhập ITviec (cập nhật cookie)

> Cookie ITviec **hết hạn ~1 năm**, nếu thấy tỷ lệ `salary_status = "auth_gated"` tăng đột biến thì cần re-login:

```bash
# Cần .env có ITVIEC_EMAIL/ITVIEC_PASSWORD
python crawler/scripts/login_itviec.py
```

Script sẽ lưu cookie vào `data/metadata/itviec_cookies.json`.

---

## 🧪 Chạy Pipeline (Load + Transform → Silver → Gold)

Từ **gốc dự án** (nơi có module `pipeline/`):

```bash
# Chạy cho từng nguồn
python -m orchestrator.run_pipeline --source itviec --date 2026-08-01
python -m orchestrator.run_pipeline --source topcv --date 2026-08-01
```

**Luồng pipeline**: Merge → Parse → Clean → Normalize → Salary Convert → Validate → Enrich → Dedup → Parquet.

**Output**:
- `data/normalized/{source}/{date}/normalized.jsonl` (Silver)
- `data/enriched/{source}/{date}/enriched.jsonl` (Golden Schema)
- `data/clean/year=YYYY/month=MM/jobs_{source}_{date}.parquet` (Gold, per-source)
- `data/rejected/{source}/{date}/rejected.jsonl` (log bản ghi lỗi)

---

## 🏆 Tạo Gold Layer gộp chéo nguồn (Cross-Source)

> Pipeline chạy dedup **riêng từng source** — để có Gold layer thống nhất (dedup chéo nguồn giữa ITviec và TopCV), chạy script gộp:

```bash
python -m logs._build_gold_merged
```

**Output**: `data/clean/year=2026/month=08/jobs_2026-08-01.parquet` (Gold layer thống nhất)

> Script này đọc `data/enriched/{itviec,topcv}/{date}/enriched.jsonl`, gộp lại, chạy `cross_source_dedupe.deduplicate()` trên toàn bộ rồi xuất 1 file parquet duy nhất.

---

## ✅ Chạy Audit chất lượng dữ liệu

```bash
python audit_data_quality.py
```

Kiểm tra: **Completeness** (null/empty), **Consistency** (locations, salary_status), **Uniqueness** (dedup), **Anomalies** (salary, posted_date).

---

## 🧪 Chạy Unit Tests

```bash
# Từ gốc dự án
python -m pytest pipeline/tests -v
```

Các bộ test chính:
- `test_shared_clean.py` — làm sạch text
- `test_shared_normalize.py` — chuẩn hóa locations
- `test_shared_salary_convert.py` — quy đổi lương
- `test_skill_extractor.py` — trích xuất kỹ năng
- `test_cross_source_dedupe.py` — khử trùng chéo nguồn
- `test_shared_validate.py` — validation
- `test_source_adapter_contract.py` — contract parser

---

## 🗂️ Mô tả data layers

| Layer | Đường dẫn | Nội dung |
|---|---|---|
| **Bronze (raw)** | `data/raw/{source}/{date}/` | HTML thô + JSONL meta từ crawler |
| **Silver (normalized)** | `data/normalized/{source}/{date}/` | Dữ liệu đã parse/clean/normalize |
| **Silver (enriched)** | `data/enriched/{source}/{date}/` | Golden schema (JobPosting) + skills |
| **Gold (clean)** | `data/clean/year=Y/month=M/` | Parquet cuối (dedup) |
| **Rejected** | `data/rejected/{source}/{date}/` | Bản ghi bị loại (kèm reason) |
| **Metadata** | `data/metadata/` | cookie, crawl_log, unrecognized_skills |

---

## 🛠️ Luồng xử lý chi tiết

```
Listing + Detail HTML (crawler)
        │
        ▼
merge_raw_records()  ──►  RawRecord
        │
        ▼
parse.py (itviec/topcv)  ──►  SourceNormalized
        │
        ▼
shared_clean()  ──►  dedupe text, dọn whitespace
        │
        ▼
shared_normalize()  ──►  chuẩn hóa locations
        │
        ▼
shared_salary_convert()  ──►  quy đổi về Triệu VND
        │
        ▼
shared_validate()  ──►  reject rác, gắn data_completeness
        │
        ▼
shared_enrich()  ──►  trích xuất skills → JobPosting
        │
        ▼
cross_source_dedupe()  ──►  gộp job trùng chéo nguồn
        │
        ▼
store_to_parquet()  ──►  Gold layer (Parquet)
```

---

## 📄 Ghi chú

- **Lương**: Quy đổi về **Triệu VND/tháng** (`salary_currency = "VND (Millions)"`).
- **Kỹ năng**: `skills_taxonomy.py` là nguồn chính; kỹ năng chưa nhận diện được log vào `data/metadata/unrecognized_skills.jsonl` để cập nhật taxonomy theo.
- **Cookie**: Cookie ITviec có thời hạn; cần re-login định kỳ (xem mục "Đăng nhập ITviec").
- **Dedup**: `cross_source_dedupe.py` khử trùng theo `(tên công ty chuẩn hóa, độ tương đồng title, chồng lấn location, salary range)`.

---

## 📌 Tóm tắt chuỗi lệnh chạy nhanh

```bash
# 1. Kích hoạt môi trường
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # Linux/macOS

# 2. Cài đặt
pip install -r crawler/requirements.txt
pip install pandas pyarrow duckdb pydantic flashtext lxml python-dotenv requests
playwright install chromium

# 3. (Nếu cần) Re-login ITviec
python crawler/scripts/login_itviec.py

# 4. Crawl
.\crawler\scripts\run_all_spiders.ps1 -BatchDate "2026-08-01"

# 5. Chạy pipeline
python -m orchestrator.run_pipeline --source itviec --date 2026-08-01
python -m orchestrator.run_pipeline --source topcv --date 2026-08-01

# 6. Tạo Gold layer gộp chéo nguồn
python -m logs._build_gold_merged

# 7. Audit
python audit_data_quality.py

# 8. Test
python -m pytest pipeline/tests -v
