# Plan giai đoạn tiếp theo — hoàn thiện Phase 1 (`skills_taxonomy.py` → `skill_extractor.py` → `parse.py` TopCV → contract test)

> Phạm vi: **chỉ** 4 file dưới đây — không lan sang `shared_validate.py`/`cross_source_dedupe.py`/`store/` (những phần đó vẫn ở trạng thái 🔴 trong `job_data_project_structure_v2.md` mục 5, làm sau). Bạn tự triển khai, tôi phân tích thiết kế + điểm cần chú ý dựa trên bằng chứng thật đã có.

---

## 1. `pipeline/config/skills_taxonomy.py`

### Mục đích
Gazetteer cho FlashText (fallback NLP) **và** bảng canonical hoá cho mọi candidate skill (kể cả tag nguồn cung cấp sẵn) — đúng thiết kế mục 3.5: mọi skill, dù đến từ đâu, đều phải qua bước canonical hoá này.

### Dữ liệu thật đã có để khởi tạo (không phải đoán)
- TopCV job `1055808`: `NoSQL, Python, SQL, Database, Core Java`
- TopCV job `2243980` (mẫu ban đầu): `Java, MongoDB, NoSQL, Redis, Kotlin, Troubleshooting, Clickhouse, Asynchronous Programming, Coroutines, OLAP, Suspend Functions, Columnar Database` (+ nice-to-have: `Performance Optimization, Distributed Systems, High Traffic`)
- ITviec job mẫu Lead Data Engineer: `AWS, Data Engineer, AWS Lambda, AWS Glue, Pandas, Python`
- ITviec job Chuyên gia Khoa học dữ liệu: `Data Engineer, Generative AI, Data Privacy/Compliance, Project Management, Data Lineage, MLOps` (+ nhiều hơn, xem file JSON layer)

### Cấu trúc đề xuất
```python
SKILLS_TAXONOMY = {
    "python": {"canonical": "Python", "aliases": ["Python", "python3", "Python3"]},
    "nodejs": {"canonical": "Node.js", "aliases": ["NodeJS", "Node.js", "Node"]},
    ...
}
```
Key là slug ổn định (không đổi khi canonical name đổi cách viết hoa/thường), `canonical` là tên hiển thị chuẩn, `aliases` là danh sách match (bao gồm chính `canonical`).

### Điểm cần quyết định trước khi viết
- **Không cần đầy đủ ngay** — chỉ cần đủ cho skill đã thấy thật ở trên (~25 skill). Phần thiếu sẽ lộ ra qua `vocab_gap_logger.py` khi chạy `parse.py` thật, bổ sung dần.
- Case-sensitivity khi match: `"NoSQL"` vs `"nosql"` — nên lowercase cả candidate lẫn alias trước khi so khớp, giữ `canonical` đúng hoa/thường chuẩn để hiển thị.

---

## 2. `pipeline/tools/skill_extractor.py`

### Logic đã chốt (mục 3.5, copy nguyên để bạn triển khai đúng)
```python
def extract_skills(record: SourceNormalized, registry_entry: dict) -> dict:
    if not registry_entry["provides_skill_tags"]:
        skills = flashtext_extractor.run(record.description_raw)
        return {"skills_all": skills, "skills_required": skills, "skills_nice_to_have": []}
    structure = registry_entry["skill_tag_structure"]
    if structure == "flat":
        skills = record.source_extra["skills"]
        return {"skills_all": skills, "skills_required": skills, "skills_nice_to_have": []}
    if structure == "grouped":
        req = record.source_extra.get("skills_required", [])
        nice = record.source_extra.get("skills_nice_to_have", [])
        return {"skills_all": req + nice, "skills_required": req, "skills_nice_to_have": nice}
```

### Cần thêm — bước canonical hoá chưa có trong pseudocode trên
Pseudocode ở tài liệu thiết kế mới dừng ở bước "lấy candidate", chưa có bước canonical hoá qua `skills_taxonomy.py`. Cần thêm 1 bước cuối: mỗi string trong `skills_all`/`skills_required`/`skills_nice_to_have` phải map qua taxonomy — match được thì thay bằng `canonical`, không match được thì **giữ nguyên string gốc** (không loại bỏ) + ghi vào `vocab_gap_logger.py`.

### Test bắt buộc trước khi coi là xong
Chạy hàm này trên **cả 2 case thật đã biết**:
- TopCV `1055808`: `skill_tag_structure="grouped"`, chỉ có `skills_required`, `skills_nice_to_have=[]` — hàm phải không lỗi.
- ITviec: `skill_tag_structure="flat"` — verify output không trùng lặp giữa `skills_all` và `skills_required` (theo pseudocode hiện tại, nhánh `flat` set `skills_required` = toàn bộ `skills_all`, có thể gây hiểu nhầm khi đọc dashboard sau này — cân nhắc để `skills_required=None` thay vì trùng `skills_all` cho nhánh `flat`, vì ITviec không thực sự phân biệt required/nice-to-have).

---

## 3. `pipeline/sources/topcv/parse.py`

### Input/Output
`RawRecord` (đã có `raw_html_detail`, `raw_html_listing`, `title_listing`, `title_detail`...) → `SourceNormalized`.

### Các điểm bắt buộc đúng theo bằng chứng thật (không phải giả định)
| Field | Cách lấy | Bằng chứng |
|---|---|---|
| `title` | `h1.box-header-job__title` + `xpath("string(.)")` trên `raw_html_detail`, **không dùng** `raw_html_listing`/`title_listing` hay `title_detail` cũ (dính bug `"Tuyển...làm việc tại..."`) | Verify trên `job_id=1055808` thật, cho ra `"Data Engineer"` sạch |
| `company_name` | Cần tìm selector riêng (chưa verify trong plan này) — gợi ý: tìm trong "Thông tin chung" hoặc header box | *(bạn tự verify khi code, không có sẵn trong các lần kiểm tra trước)* |
| `source_extra["skills_required"/"skills_nice_to_have"/"skills_industry"]` | `div.required-tags`, 3 nhóm theo `class="required-tag__content--title"` đứng trước mỗi nhóm | Verify — nhưng **PHẢI tolerant thiếu nhóm** (job `1055808` chỉ có 1/3) |
| `work_mode` | Section "Thông tin chung", nhãn `"Hình thức làm việc"` → map `"Onsite"`/`"Làm việc tại văn phòng"` → `WorkMode.ONSITE` | Verify trên `job_id=1055808`: `"Làm việc tại văn phòng / Onsite"` |
| `salary_status` | TopCV không có `AUTH_GATED` — chỉ `DISCLOSED` (có số) hoặc `NEGOTIABLE` ("Thoả thuận") | Theo `SOURCE_REGISTRY["topcv"]["salary_can_be_gated"]=False` |
| `posted_date_raw` | Giữ nguyên string thô (`"6 ngày trước"`) — **không** parse ra date thật ở đây, đó là việc của `date_parser.py` (chưa viết, giai đoạn sau) | — |

### Case phải xử lý được, không raise lỗi
- `raw.detail_crawled=False` (37/55 job hiện tại) — `parse.py` vẫn phải chạy được, dùng dữ liệu từ `raw_html_listing`/`title_listing` thôi, `description_raw` có thể rỗng, `salary_status=NOT_PROVIDED`.
- Job dạng `/brand/...` (đã gặp `job_id=2237041` có title hỏng ở bug cũ) — parse.py không tự động tin `title_detail`, đã tránh được nhờ dùng lại `h1` trực tiếp thay vì field `title` cũ trong JSONL.

### Gate trước khi coi Phase 1 xong
Chạy `parse.py` trên **toàn bộ 18 RawRecord có detail** từ `merge.py` (đã test thật ở lượt trước) — không raise lỗi job nào, spot-check bằng mắt 2-3 job để xác nhận `title`/`skills`/`work_mode` đúng.

---

## 4. `pipeline/tests/contract/test_source_adapter_contract.py`

### Logic đã chốt (mục 3.6)
```python
@pytest.mark.parametrize("source_name", SOURCE_REGISTRY.keys())
def test_adapter_conforms(source_name):
    adapter = load_adapter(source_name)
    sample = adapter.parse(load_fixture(source_name, "case_a_full"))
    assert isinstance(sample, SourceNormalized)
    assert sample.locations and isinstance(sample.locations, list)
    assert sample.salary_status in SalaryStatus
    assert sample.description_raw.strip() != ""
    assert set(sample.model_fields) == CORE_FIELD_NAMES
```

### Vấn đề cần giải quyết trước khi chạy được
- `SOURCE_REGISTRY.keys()` gồm cả `itviec` — nhưng `sources/itviec/parse.py` **chưa viết** (ngoài phạm vi plan này). Nếu chạy test parametrize theo toàn bộ registry, test ITviec sẽ fail vì chưa có adapter — cần `pytest.mark.skip` tạm cho `itviec` kèm comment rõ lý do, không xoá test case.
- `load_fixture(source_name, "case_a_full")` — cần 1 file fixture thật. Đề xuất: dùng chính `RawRecord` build từ `job_id=1055808` (đã có `raw_html_detail` thật, đã verify đủ dữ liệu) làm fixture `case_a_full` cho TopCV, không cần tạo dữ liệu giả.
- `assert sample.locations and ...` — sẽ fail nếu job không xác định được location. Cần verify `job_id=1055808` có location rõ ràng trước khi dùng làm fixture (chưa verify trong các lượt trước — bạn tự kiểm tra khi code).

---

## Không thuộc phạm vi plan này (để sau)

`sources/itviec/parse.py`, `shared_validate.py`, `shared_clean.py`/`shared_normalize.py`/`shared_salary_convert.py`, `cross_source_dedupe.py`, `store/`, `title_classifier.py`/`flag_extractor.py`, `orchestrator/run_pipeline.py` — giữ nguyên trạng thái 🔴/🟡 như mục 5 `job_data_project_structure_v2.md` đã ghi, chưa động tới.

## Sau khi xong 4 file trên — báo lại gì

- Kết quả chạy `parse.py` trên 18 job TopCV thật (bao nhiêu lỗi, field nào hay thiếu).
- Nội dung thật của `skills_taxonomy.py` bạn đã viết (để tôi verify coverage so với skill thật đã thấy).
- Bất kỳ selector nào bạn phải tự tìm thêm ngoài bảng ở mục 3 (đặc biệt `company_name`) — tôi chưa verify được vì chưa từng kiểm tra selector này trên HTML thật.
