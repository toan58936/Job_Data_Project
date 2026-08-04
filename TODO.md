# TODO — ELT Audit Remediation & Re-run

## Bước 1 — Cập nhật skills_taxonomy.py (P0)
- [x] Thêm 26 skills phổ biến từ unrecognized_skills.jsonl (dbt, airflow, terraform, fastapi, nextjs, svelte, rust, golang, playwright, grafana, prometheus, pulumi, remix, supabase, clickhouse, datadog, langchain, bun, tanstack, htmx, ...)
- [x] Thêm aliases (NextJS→Next.js, Golang→Go, Pyspark→PySpark, fastapi→FastAPI, ...)
- [x] Viết test đảm bảo taxonomy phủ các skills tần suất cao

## Bước 2 — sửa shared_salary_convert.py (P0)
- [x] Xử lý "nghìn" trong regex unit
- [x] Xử lý annual/yearly salary (chia 12)
- [x] Bỏ hardcode tỷ giá → đọc từ config/fallback
- [x] Viết test cho các case mới

## Bước 3 — sửa skill_extractor.py (P1)
- [x] Thêm regex headers tiếng Việt vào `_split_text_by_context` ("Yêu cầu", "Kỹ năng", "Mô tả", ...)
- [x] Viết test cho case tiếng Việt

## Bước 4 — sửa shared_normalize.py (P1)
- [x] Bổ sung mapping location tiếng Anh (Ha Noi, Ho Chi Minh, HCM, Binh Duong, Da Nang)
- [x] Viết test

## Bước 5 — sửa cross_source_dedupe.py (P2)
- [x] Thêm salary_range làm tín hiệu phụ (chênh > 50% → không gộp)
- [x] Viết test

## Bước 6 — cookie ITviec + TopCV parse (P0/P3)
- [x] Cập nhật itviec_cookies.json (re-login)
- [x] TopCV: xử lý "Cạnh tranh" salary → negotiable
- [x] TopCV: parse posted_date đúng (tránh nhầm hạn nộp)

## Bước 7 — shared_validate.py (P2)
- [x] Validate locations/work_mode required
- [x] Validate salary_min < salary_max
- [x] Viết test

## Bước 8 — Re-run pipeline + Audit
- [x] Chạy lại run_pipeline.py cho 2026-08-01 (itviec ✅ 45 enriched, topcv ✅ 57 enriched)
- [x] Chạy lại audit_data_quality.py / _verify_fixes_after_rerun.py
  - Completeness: title/company/locations/work_mode/job_skills đều ✅ (0% null/empty)
  - Locations: tất cả đã chuẩn hóa ✅
  - Salary anomalies: 0 (hết bug 1.2B và 0) ✅
  - Posted_date tương lai: 0 ✅
  - Skills mới: 20/26 taxonomy mới xuất hiện trong dữ liệu ✅
  - Còn lại: 6 records disclosed chỉ có 1 biên min/max (dạng "Up To X"/"From X") — chấp nhận được
- [x] Tạo Gold layer gộp chéo nguồn: `logs/_build_gold_merged.py`
  - 102 enriched → 96 gold (dedup chéo nguồn loại 6 job trùng)
  - Lưu `data/clean/year=2026/month=08/jobs_2026-08-01.parquet`
  - Audit cuối: 96 records, các chỉ số đều PASS
