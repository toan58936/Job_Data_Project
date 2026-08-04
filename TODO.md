# TODO — Role Normalization & Gold Layer cho Dashboard

Kế hoạch triển khai chuẩn hóa vai trò công việc (canonical `job_role`) và tinh gọn
Gold layer phục vụ dashboard. Quyết định đã chốt với user:
- Chỉ giữ `job_role` canonical (data_engineer, data_analyst, ...) — bóc tách từ title.
- Loại bỏ `job_expertise`/`job_domains`/`url`/`description_raw`/`source_extra`/`data_completeness`/`crawled_at`/`listing_position` khỏi Gold.
- Giữ `job_id` + `source` làm khoá join sang enriched để xem job gốc khi cần.

## Các bước thực hiện

- [x] **R1.** Tạo `pipeline/tools/role_extractor.py` — module nhận diện canonical role từ title/expertise (data_engineer, data_analyst, data_scientist, ml_engineer, data_architect, bi_analyst, ai_engineer, devops, backend, frontend, qa, ...)
- [x] **R2.** Viết test `pipeline/tests/test_role_extractor.py` (EN + VI)
- [x] **R3.** Cập nhật `pipeline/model/job_posting.py` — thêm field `job_role: Optional[str] = None`
- [x] **R4.** Cập nhật `pipeline/pipeline_steps/shared_enrich.py` — gọi `extract_seniority()` (bỏ hardcode `None`) + `extract_role()` để điền `job_role`
- [x] **R5.** Cập nhật `pipeline/store/duckdb_store.py` — thêm `store_to_gold()` chỉ ghi các cột phân tích được
- [x] **R6.** Cập nhật `logs/_build_gold_merged.py` — chuyển sang `store_to_gold()` để tạo Gold file chuẩn
- [x] **R7.** Chạy pytest toàn bộ để đảm bảo không vỡ test cũ
- [x] **R8.** Re-run pipeline (itviec + topcv) → build Gold layer → verify role + seniority
- [x] **R9.** Cập nhật `README.md` và `TODO.md` phản ánh tính năng mới

## Kết quả R8 (verify)

- Enriched itviec: 45 bản ghi — `job_role` điền 44/45 (97.8%), `seniority_level` 32/45 (71%).
- Enriched topcv: 57 bản ghi — `job_role` điền 43/57 (75.4%), `seniority_level` 43/57 (75.4%).
- Gold layer: `data/gold/year=2026/month=08/jobs_2026-08-01.parquet` (96 records sau dedup).
- Gold columns: gồm `job_role` (non-null 81/96) + `seniority_level` (non-null 69/96) → đã có đủ cho dashboard phân tích.

## Phần B đã hoàn thành (Seniority Level Normalization)

- [x] B1. Tạo `pipeline/tools/seniority_extractor.py`
- [x] B2. Cập nhật `shared_enrich.py` — gọi `extract_seniority()`
- [x] B3. Viết test `pipeline/tests/test_seniority_extractor.py`
- [x] B4. Cập nhật `logs/_verify_role_seniority.py`
- [x] B5. Chạy pytest toàn bộ
- [x] B6. Re-run pipeline → build Gold layer → verify seniority
- [x] B7. Cập nhật `README.md` và `TODO.md`
