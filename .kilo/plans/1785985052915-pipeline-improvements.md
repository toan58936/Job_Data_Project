# Plan: Pipeline Improvements Phase

## Context
Crawler đã ổn định (batch 2026-08-06: 45 ITviec + 53 TopCV, 100% detail coverage, 0 failed).
Pipeline chạy thành công nhưng có 3 điểm cần cải thiện:
1. Salary parse success thấp (ITviec 22.2%, TopCV 41.5%)
2. TopCV role extraction thấp (73.6% vs ITviec 97.8%)
3. Không có metrics export / dashboard

---

## Task 1: Cải thiện Salary Parse Success

### Root cause analysis (updated sau khi đào HTML thật)

Đã sample 3 ITviec + 51 TopCV detail HTML files từ batch 2026-08-06:

**ITviec:**
- `salary_range` trong JSON data layer: `"You'll love it"` (placeholder marketing của ITviec cho "không công bố lương") hoặc `"1,200 - 2,000 USD"`
- HTML display: `<span class="ips-2 fw-500">1,200 - 2,000 USD</span>`
- Parser ITviec (`itviec/parse.py:100-157`) đã extract `salary_raw` đúng cả 2 loại
- ~78% ITviec jobs dùng `"You'll love it"` → đây là **hành vi site**, không phải bug parser

**TopCV:**
- Tất cả 51 files có `box-header-job__salary--title` — selector nhất quán
- Giá trị: `Thoả thuận` (negotiable) hoặc `20 - 70 triệu` (disclosed)
- Parser TopCV (`topcv/parse.py:290-313`) extract đúng
- Có thêm `qgTracking` JS object chứa `salary_range` — có thể dùng làm fallback sau này
- ~59% TopCV jobs là `Thoả thuận` hoặc không có lương — cũng là **hành vi site**

**Kết luận từ HTML analysis:**
- HTML extraction **KHÔNG** bị missing pattern nghiêm trọng
- Root cause thực sự nằm ở `shared_salary_convert.py` edge cases
- **Improvement expected: 2-5%** (marginal) — vì nguyên nhân chính là employers không disclose salary
- Không nên kỳ vọng cải thiện đột biến

### Implementation
**File: `pipeline/pipeline_steps/shared_salary_convert.py`**

1. Thêm unit detection cho per-hour/per-day/per-week (lines ~108-144):
   - `has_per_hour = any(w in cleaned for w in ("giờ", "/h", "per hour", "hourly"))`
   - `has_per_day = any(w in cleaned for w in ("ngày", "/d", "per day", "daily"))`
   - `has_per_week = any(w in cleaned for w in ("tuần", "/w", "per week", "weekly"))`
   - Nếu phát hiện → log warning + return None (không đủ thông tin quy về tháng)

2. Fix "k" detection (line 113):
   - Thay `"k "` → `r"\bk\b"` (word boundary)
   - Hoặc `any(w in cleaned for w in ("nghìn", "ngàn", "thousand", "k "))` → thêm `re.search(r"\bk\b", cleaned)`

3. Thêm negotiable markers (line 36-38):
   - Thêm: `"thỏa thuận lương"`, `"lương thỏa thuận"`, `"trao đổi"`, `"upon agreement"`

4. Strip prefix "Lương:" / "Lương" trước khi parse (line 98):
   - `cleaned = re.sub(r"^(lương\s*[:\-]?\s*)", "", cleaned, flags=re.IGNORECASE)`

### Validation
- Chạy `python -c "from pipeline.pipeline_steps.shared_salary_convert import parse_and_convert_salary; ..."` với test cases:
  - `"15k USD"` → 375.0 triệu/tháng
  - `"Lương: 20 triệu"` → 20.0
  - `"Thỏa thuận lương"` → (None, None)
  - `"10 USD/giờ"` → (None, None) với warning

### Note
- **Không cần sửa HTML parsers** — đã xác nhận extraction đúng 100%
- **Không kỳ vọng improvement lớn** — site behavior là nguyên nhân chính
- Fix này là để xử lý edge cases còn sót lại, không phải để "bắt hết salary"

---

## Task 2: Cải thiện TopCV Role Extraction

### Root cause analysis (updated — HTML + title deep dive)
- `role_extractor.py:191-219` — `extract_role(title, expertise)` — TopCV không có `job_expertise_raw`.
- Analyzed actual TopCV titles from batch 2026-08-06: 13/44 unique titles bị FAIL (70.5% rate)
- ITviec: 1/42 FAIL (97.6%) — "Chief AI Transformation Officer-CAITO, Data Warehousing"

FAIL titles + target role mapping:
| Title | Target Role | Reason |
|-------|-------------|--------|
| "Chuyên Viên Big Data (Middle)" | data_engineer | `\bbig\s+data\b` missing |
| "Chuyên Viên E-Com IT Application" | software_engineer | `\be-?\s*com\b` missing |
| "Chuyên Viên Kỹ Thuật Dữ Liệu" | data_engineer | `\bkỹ\s+thuật\s+dữ\s+liệu\b` missing (có `kỹ\s+sư` nhưng không có `kỹ\s+thuật`) |
| "Chuyên Viên Phát Triển Giải Pháp CNTT" | software_engineer | `\bphát\s+triển\s+giải\s+pháp\b` missing |
| "Chuyên Viên Xử Lý Dữ Liệu" | data_analyst | `\bxử\s+lý\s+dữ\s+liệu\b` missing |
| "Data Intelligence Lead" | data_analyst | `\bdata\s+intelligence\b` missing |
| "Data Solution Consultant" | data_engineer | `\bdata\s+solution\b` missing |
| "Head Of Data" | data_engineer | `\bhead\s+of\s+data\b` missing |
| "IT Infrastructure Engineer/ Data Center Storage" | devops_engineer | `\binfrastructure\b`, `\bdata\s+center\b` missing |
| "IT Server & Database Engineer" | devops_engineer | `\bit\s+server\b` missing |
| "Kỹ Sư Giải Cứu Dữ Liệu" | data_engineer | `\bgiải\s+cứu\s+dữ\s+liệu\b` missing |
| "Senior Operations Data Specialist" | data_analyst | `\bdata\s+specialist\b` missing |
| "Spark ETL (Dự Án Chuyển Đổi Số)" | data_engineer | `\betl\b` missing (chỉ có `\betl\s+engineer` — không match "Spark ETL") |
| "Tìm việc làm nhanh 24h..." | None (junk title) | Expected — not a real job title |

### Implementation (completed)
**Files changed:**
1. `pipeline/tools/role_extractor.py` — 5 role buckets updated
2. `pipeline/pipeline_steps/shared_enrich.py` — line 40 updated
3. `pipeline/tests/test_role_extractor.py` — 22 new tests added (total: 33)

**Patterns added to `_ROLE_PATTERNS`:**
- `data_engineer`: `\bbig\s+data\b`, `\bkỹ\s+thuật\s+dữ\s+liệu\b`, `\bhead\s+of\s+data\b`, `\bdata\s+solution\b`, `\bgiải\s+cứu\s+dữ\s+liệu\b`, `\betl\b`
- `data_analyst`: `\bxử\s+lý\s+dữ\s+liệu\b`, `\bdata\s+intelligence\b`, `\bdata\s+specialist\b`
- `software_engineer`: `\bphát\s+triển\s+giải\s+pháp\b`, `\be-?\s*com\b`
- `devops_engineer`: `\binfrastructure\b`, `\bit\s+server\b`, `\bdata\s+center\b`
- `engineering_manager`: `\btrưởng\s+nhóm\s+kỹ\s+thuật\b`, `\bgiám\s+đốc\s+công\s+nghệ\b`, `\bcto\b`
- `solution_architect`: `\bkiến\s+trúc\s+sư\s+công\s+nghệ\b`

**extract_role() signature extended:**
```python
def extract_role(title, expertise=None, requirements_text=None) -> Optional[str]
```
Fallback chain: title → expertise → requirements_text (for TopCV which lacks expertise)

**shared_enrich.py:40 update:**
```python
job_role = extract_role(
    record.title,
    job_expertise,
    record.source_extra.get("requirements_raw", ""),
)
```

### Results (verified)
- Gold layer: 93 records → **92/93 job_role assigned (98.9%)**
- ITviec: 42/42 titles → 100% (was 97.6%)
- TopCV: 43/44 titles → 97.7% (was 70.5%)
- Only remaining None: junk title "Tìm việc làm nhanh 24h, việc làm mới nhất trên toàn quốc"
- 15/15 unit tests pass, 33/33 role extractor tests pass

---

## Task 3: Thêm pipeline_metrics.parquet Export

### Implementation
**File mới: `pipeline/pipeline_steps/metrics_export.py`**

```python
def export_metrics(metrics: dict, batch_date: str) -> Path:
    """Ghi pipeline metrics ra data/metrics/pipeline_metrics_{batch_date}.parquet"""
```

**Metrics schema:**
| Field | Type | Description |
|---|---|---|
| `batch_date` | str | Ngày crawl |
| `source` | str | itviec/topcv |
| `stage` | str | listing/detail/merge/parse/validate/enrich/dedupe |
| `metric_name` | str | Tên metric |
| `metric_value` | float/int | Giá trị |
| `metric_unit` | str | count/pct/... |

**Metrics cần capture:**
- Listing: `listing_count`, `listing_html_count`
- Detail: `detail_count`, `detail_html_count`, `detail_coverage_pct`, `failed_count`
- Parse: `salary_disclosed_count`, `salary_disclosed_pct`
- Validate: `valid_count`, `rejected_count`, `rejection_pct`
- Enrich: `skills_non_empty_count`, `skills_non_empty_pct`, `locations_non_empty_pct`, `work_mode_present_pct`, `role_present_pct`, `seniority_present_pct`
- Dedupe: `before_dedupe_count`, `after_dedupe_count`, `dedupe_ratio_pct`

**Integration:**
- Thêm vào `orchestrator/run_pipeline.py` sau mỗi stage
- Thêm vào `orchestrator/run_cross_source.py` sau cross-source dedupe

**File: `orchestrator/run_pipeline.py`** — thêm call sau stage 3 (validate), stage 4 (enrich), stage 5 (dedupe)

---

## Task 4: Streamlit Dashboard

### Implementation
**File mới: `dashboard/app.py`**

**Tech stack:**
- Streamlit (đã có trong project?)
- DuckDB để query parquet trực tiếp (nhanh, không cần load toàn bộ vào memory)
- Plotly cho charts

**Pages:**
1. **Overview** — tổng quan batch jobs: line chart job count theo ngày, pie chart by source
2. **Quality** — completeness metrics table, salary disclosure rate, skills coverage
3. **Salary Analysis** — histogram salary_min/max, box plot by role, by location
4. **Skills & Roles** — top skills bar chart, role distribution, seniority distribution
5. **Data Explorer** — filter + table view của gold layer

**Data source:**
- Read từ `data/gold/year=*/month=*/jobs_*.parquet` qua DuckDB
- Read từ `data/metrics/pipeline_metrics_*.parquet` qua DuckDB

**Run command:**
```bash
streamlit run dashboard/app.py
```

---

## Execution Order

| Task | Priority | Estimated complexity | Dependencies |
|---|---|---|---|
| Task 1: Salary parse fix | P1 | Low (1 file, ~30 lines) | None |
| Task 2: Role extraction fix | P1 | Low (2 files, ~20 lines) | None |
| Task 3: Metrics export | P2 | Medium (2 new + 2 modified files) | Task 1, 2 (để capture improved metrics) |
| Task 4: Dashboard | P3 | Medium (1 new file, ~200 lines) | Task 3 (metrics parquet) |

---

## Validation Plan

### After Task 1
```bash
# Unit test salary parser
python -c "
from pipeline.pipeline_steps.shared_salary_convert import parse_and_convert_salary
tests = {
    '15k USD': (375.0, 375.0),
    '20 - 35 triệu': (20.0, 35.0),
    'Lương: 25 triệu': (25.0, 25.0),
    'Thỏa thuận lương': (None, None),
    '1000 USD/năm': (83.3, 83.3),  # 1000/12 * 25.4/1000 * 1000 = 83.3
}
for inp, expected in tests.items():
    result = parse_and_convert_salary(inp)
    print(f'{inp}: {result} (expected {expected})')
"

# Re-run pipeline and check salary_disclosed rate
PYTHONPATH=. python -X utf8 orchestrator/run_pipeline.py --source itviec --date 2026-08-06
```

### After Task 2
```bash
# Unit test role extractor with Vietnamese TopCV titles
python -c "
from pipeline.tools.role_extractor import extract_role
tests = [
    ('Kỹ sư Dữ liệu', None, 'data_engineer'),
    ('Trưởng nhóm Kỹ thuật', None, 'engineering_manager'),
    ('Chuyên viên Phân tích Dữ liệu', None, 'data_analyst'),
]
for title, expertise, expected in tests:
    result = extract_role(title, expertise)
    print(f'{title}: {result} (expected {expected})')
"

# Re-run pipeline and check role_present rate
```

### After Task 3
```bash
# Check metrics parquet exists and has expected columns
python -c "
import duckdb
from pathlib import Path
p = Path('data/metrics/pipeline_metrics_2026-08-06.parquet')
con = duckdb.connect(':memory:')
df = con.execute('SELECT * FROM read_parquet(?)', [str(p)]).fetch_df()
print(df.columns.tolist())
print(df.groupby('stage')['metric_name'].count())
"
```

### After Task 4
```bash
# Launch dashboard
streamlit run dashboard/app.py
# Manual verification: each page loads, charts render, filters work
```

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Salary parser change breaks existing working cases | Add regression test cases from current production data before changing |
| Role patterns overlap (e.g., "data engineer" vs "data analyst") | Keep priority order, more specific patterns first |
| Metrics parquet grows unbounded | Partition by batch_date, add retention policy (keep 90 days) |
| Dashboard slow on large datasets | Use DuckDB lazy evaluation, add date filters |

---

## Out of Scope
- Không thêm nguồn crawl mới
- Không thay đổi schema JobPosting/SourceNormalized
- Không implement retry_failed.py (đã có trong plan cũ)
- Không cải thiện ITviec/TopCV HTML parsers (đã ổn định)
