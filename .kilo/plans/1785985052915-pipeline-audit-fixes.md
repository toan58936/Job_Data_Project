# Implementation Plan — Comprehensive Pipeline Audit Fixes

**Source:** `comprehensive_pipeline_audit.md` (322 lines, 10 gaps identified)
**Strategy:** Fix P1 first (data correctness), then P2 (architecture/robustness), then P3 (nice-to-have).

---

## P1 — Data Correctness (Fix bugs that cause wrong output)

### Task 1.1: Fix `business_analyst` misclassified as `technical_writer`
- **File:** `pipeline/tools/role_extractor.py:171-175`
- **Change:**
  - Remove `r"\bbusiness\s+analyst\b"` and `r"\bchuyên\s+viên\s+phân\s+tích\s+nghiệp\s+vụ\b"` from `technical_writer` entry
  - Add new `"business_analyst"` entry to `_ROLE_PATTERNS` with those 2 patterns
  - Place before `data_analyst` (more specific first)
- **Validation:** Run `pytest pipeline/tests/contract/test_source_adapter_contract.py -k "itviec or topcv"` — role for "Business Analyst" titles should return `business_analyst`, not `technical_writer`

### Task 1.2: Truncate `description_raw` passed to `seniority_extractor`
- **File:** `pipeline/pipeline_steps/shared_enrich.py:24`
- **Change:** Pass `record.description_raw[:500]` instead of full `description_raw` to `extract_seniority()`
- **Rationale:** Full description contains phrases like "experience working with senior stakeholders" that cause false positive `senior` classification
- **Validation:** Unit test: title "Data Engineer" + description containing "senior stakeholders" → `seniority_level` should be `None` (not `senior`)

### Task 1.3: Add `seniority` signal to `_salary_compatible` in dedupe
- **File:** `pipeline/pipeline_steps/cross_source_dedupe.py:41-63`
- **Change:**
  - Import `extract_seniority` (or use `job.seniority_level` if already on `JobPosting`)
  - In `_salary_compatible`, when both salaries are `None`, also check `seniority_level`: if different (`junior` vs `senior`), return `False` (not compatible)
- **Validation:** Integration test: 2 jobs same company/title, one `junior` one `senior`, both salary `None` → should NOT dedupe

---

## P2 — Architecture & Robustness

### Task 2.1: Fix `SOURCE_REGISTRY` fallback missing keys
- **File:** `orchestrator/run_pipeline.py:22-25`
- **Change:** Complete fallback registry with all keys: `requires_browser`, `has_ajax_preview`, `has_json_data_layer`, `provides_skill_tags`, `skill_tag_structure`, `salary_can_be_gated`, `id_strategy`
- **Validation:** Simulate ImportError for `shared.source_registry` → pipeline should not crash with KeyError

### Task 2.2: Add `batch_date` to `GOLD_ANALYZABLE_COLUMNS`
- **File:** `pipeline/store/duckdb_store.py:53-68`
- **Change:** Add `"batch_date"` to `GOLD_ANALYZABLE_COLUMNS` list
- **Validation:** After running pipeline, query Gold parquet → `batch_date` column should exist and contain values

### Task 2.3: Add per-batch dedup in `vocab_gap_logger`
- **File:** `pipeline/tools/vocab_gap_logger.py`
- **Change:**
  - Add module-level `_seen_skills: set[str] = set()` with lock protection
  - Before writing, check if `skill_text` already in `_seen_skills`; if yes, skip write
  - Add `log_unrecognized_role(title, source, job_id)` function similar to skill logger
- **Validation:** Run pipeline with 100 jobs → `unrecognized_skills.jsonl` should have unique entries only

### Task 2.4: Handle "Toàn quốc" / "Remote" / "Overseas" locations
- **File:** `pipeline/pipeline_steps/shared_normalize.py:110-116`
- **Change:** Add patterns to `_EXTRA_PATTERNS` or `_PROVINCES`: `"toàn quốc"` → `"All"`, `"remote"` → `"Remote"`, `"overseas"` → `"Overseas"`
- **Validation:** Input `"Toàn quốc"` → normalized location should be `"All"`, not raw `"Toàn quốc"`

---

## P3 — Observability & Edge Cases

### Task 3.1: Extend `date_parser.py` with ISO format
- **File:** `pipeline/tools/date_parser.py:30`
- **Change:** Add `_ISO_PATTERN = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")` and `parse_iso_date()` function; call it in `parse_vietnamese_date()` before falling back to relative
- **Validation:** Input `"2026-08-07"` → should parse to `date(2026, 8, 7)`

### Task 3.2: Replace deprecated `datetime.utcnow()`
- **Files:** `pipeline/pipeline_steps/shared_enrich.py:57`, `pipeline/tools/vocab_gap_logger.py:28`
- **Change:** Replace `datetime.utcnow().isoformat()` with `datetime.now(datetime.timezone.utc).isoformat()`
- **Validation:** No test needed — Python 3.12+ will warn if `utcnow()` is used

### Task 3.3: Add `parse_hit_rate` metric to parsers
- **Files:** `pipeline/sources/itviec/parse.py`, `pipeline/sources/topcv/parse.py`
- **Change:** Track fields successfully extracted vs. fields attempted; log warning if hit rate < 50% for a job
- **Validation:** Simulate HTML with all selectors missing → warning should appear in logs

---

## Execution Order

```
P1: 1.1 → 1.2 → 1.3      (fix wrong output first)
P2: 2.1 → 2.2 → 2.3 → 2.4  (fix architecture/robustness)
P3: 3.1 → 3.2 → 3.3      (nice-to-have)
```

## Validation Gate

After all tasks:
1. `pytest pipeline/tests/` — all tests pass
2. `pytest pipeline/tests/integration/` — integration tests pass (once fixtures are populated)
3. Run pipeline on `2026-08-06` batch → verify no new warnings, Gold layer has `batch_date` column
