# Job Data Project — Cấu trúc dự án chuẩn (v4, hợp nhất pipeline stability review)

> Bản này hợp nhất `job_data_folder_structure.md` (v1 — cây thư mục gốc), phần source-abstraction đã verify trên HTML thật (mục 1–6), `crawler_design_final.md` (kiến trúc crawl đã chốt), và bản đánh giá độ ổn định pipeline (mục 8 — MỚI). Từ nay đây là bản tham chiếu chính.
>
> Nguyên tắc xuyên suốt không đổi từ v1 (Scrapy + Playwright, monorepo, tách current/log, NLP rule-based, không LLM production) — bản này bổ sung 2 lớp còn thiếu: **(1) nguồn không được phép rò rỉ đặc thù ra ngoài `sources/{source}/`, (2) crawler và pipeline nói chung 1 join key (`job_id`), không phải `url`.**

---

## 1. Nguyên tắc thiết kế xuyên suốt (5 nguyên tắc, thêm 1 so với v1)

1. **Tách "đặc thù nguồn" khỏi "dùng chung"** — thêm nguồn mới không sửa code chung.
2. **Khai báo capability tường minh, ép buộc lúc chạy** — không tự quyết ngầm rồi lệch khỏi khai báo.
3. **Dữ liệu có vòng đời, không chỉ có/không** — mọi bảng trạng thái cuối đi kèm 1 bảng log theo thời gian.
4. **1 repo, ranh giới bằng thư mục** — chung git repo, chung cơ chế đảm bảo tên nguồn khớp nhau.
5. **[MỚI] Schema chung chỉ chứa field ≥2 nguồn xác nhận cùng có + có nhu cầu dashboard thật** — mọi field khác, dù chỉ 1 nguồn có, đi qua `source_extra` chứ không phình `SourceNormalized`. Đây là hệ quả trực tiếp của bằng chứng thật: ITviec và TopCV không có field đặc thù nào trùng nhau ngoài `title`/`company_name`/`url`/`description_raw` — nếu không có nguyên tắc 5, core schema sẽ tăng tuyến tính theo số nguồn, đúng thứ nguyên tắc 1 cấm.

---

## 2. Cây thư mục chuẩn (đã cập nhật)

```
job-data-project/
│
├── shared/
│   ├── __init__.py
│   └── source_registry.py                 # SOURCE_REGISTRY — xem 3.2, đã mở rộng field capability
│
├── crawler/                               # Scrapy — [ĐÃ ĐỔI so với v1] xem 3.7
│   ├── scrapy.cfg
│   ├── requirements.txt
│   ├── job_crawler/
│   │   ├── spiders/
│   │   │   ├── base_spider.py             # đọc has_ajax_preview để tránh bắt nhầm URL fragment
│   │   │   ├── itviec_listing_spider.py   # Phase 1 — output jobs_meta_listing.jsonl
│   │   │   ├── itviec_detail_spider.py    # Phase 2 — đọc listing JSONL, crawl /it-jobs/{slug}
│   │   │   │                              # (KHÔNG phải /content?job_index=N — AJAX fragment)
│   │   │   ├── topcv_listing_spider.py
│   │   │   ├── topcv_detail_spider.py
│   │   │   └── vietnamworks_spider.py     # placeholder, xem câu hỏi mở ở cuối file
│   │   ├── middlewares.py
│   │   ├── pipelines.py                   # route item theo job_id → listing/detail JSONL riêng
│   │   ├── items.py                       # job_id, url, title, raw_html, source, batch_date,
│   │   │                                  # listing_page_num, listing_position — xem 3.7
│   │   ├── extensions.py                  # [MỚI] ghi crawl_log.parquet khi spider_closed
│   │   └── settings.py                    # [MỚI] DOWNLOAD_DELAY, AUTOTHROTTLE, ROBOTSTXT_OBEY — xem 3.7
│   └── scripts/
│       ├── run_all_spiders.sh
│       └── cleanup_raw_html.py            # [MỚI] retention cleanup, chỉ quét raw_html/job_detail/
│
├── pipeline/
│   ├── main.py
│   ├── requirements.txt
│   │
│   ├── config/
│   │   ├── base_config.py
│   │   ├── skills_taxonomy.py
│   │   ├── title_rules.py
│   │   ├── flag_keywords.py
│   │   └── settings.py
│   │
│   ├── model/
│   │   ├── source_interface.py            # SourceAdapter Protocol — xem 3.1
│   │   ├── raw_record.py
│   │   ├── source_normalized.py           # ĐÃ ĐỔI — xem 3.3 (core + source_extra 2 tầng)
│   │   ├── job_posting.py
│   │   └── dedupe_mapping.py
│   │
│   ├── sources/                           # RIÊNG từng nguồn — implement SourceAdapter
│   │   ├── itviec/
│   │   │   ├── extract.py                 # ưu tiên đọc JSON data-layer trước, HTML sau — xem 3.4
│   │   │   └── parse.py                   # skill_tag_structure="flat"
│   │   └── topcv/
│   │       ├── extract.py
│   │       └── parse.py                   # skill_tag_structure="grouped" — tách 3 nhóm skill
│   │
│   ├── pipeline_steps/                    # CHUNG cho mọi nguồn — không import gì từ sources/
│   │   ├── merge.py
│   │   ├── shared_clean.py
│   │   ├── shared_normalize.py
│   │   ├── shared_salary_convert.py
│   │   ├── shared_validate.py             # đọc salary_can_be_gated trước khi reject salary null
│   │   ├── cross_source_dedupe.py
│   │   └── shared_enrich.py               # orchestrate: preprocess → skill extract (ưu tiên
│   │                                       # source_extra theo skill_tag_structure, fallback NLP)
│   │                                       # → title classify → flag extract
│   │
│   ├── store/
│   │   ├── base_store.py
│   │   ├── clean_db_store.py
│   │   ├── reject_store.py
│   │   └── dedupe_store.py
│   │
│   ├── tools/
│   │   ├── minhash_utils.py
│   │   ├── text_preprocessor.py
│   │   ├── skill_extractor.py             # rẽ nhánh theo skill_tag_structure — xem 3.5
│   │   ├── title_classifier.py
│   │   ├── flag_extractor.py
│   │   ├── vocab_gap_logger.py            # [SỬA] áp dụng cho CẢ 2 nhánh skill (tag có sẵn lẫn
│   │   │                                  # NLP) — không chỉ nhánh free-text như thiết kế ban đầu,
│   │   │                                  # vì tag nguồn cung cấp cũng có thể không match taxonomy
│   │   ├── date_parser.py
│   │   ├── salary_parser.py
│   │   └── text_cleaner.py
│   │
│   ├── orchestrator/
│   │   └── run_pipeline.py
│   │
│   └── tests/
│       ├── conftest.py
│       ├── contract/                      # [MỚI] test hợp đồng — xem 3.6
│       │   └── test_source_adapter_contract.py
│       ├── unit/
│       │   ├── sources/
│       │   ├── pipeline_steps/
│       │   ├── tools/
│       │   └── model/
│       ├── integration/
│       │   ├── test_end_to_end.py
│       │   └── test_cross_source_dedupe.py
│       └── fixtures/
│           ├── extract_cases/             # case_a_full ... case_e_retention_expired (5 case, v1 mục 3.9)
│           ├── raw/
│           └── expected/
│
├── data/                                  # gitignore, giữ .gitkeep — không đổi cấu trúc so với v1
│   ├── raw/{source}/{batch_date}/raw_html/{listing,job_detail}/
│   ├── normalized/{source}/{batch_date}/normalized.jsonl
│   ├── clean/
│   │   ├── jobs_current.parquet
│   │   ├── jobs_current.duckdb
│   │   ├── jobs_log.parquet
│   │   └── schema.sql                     # phải version SalaryStatus enum + source_extra struct
│   ├── rejected/{source}/{batch_date}/rejected.jsonl
│   └── metadata/
│       ├── dedupe_mapping.parquet
│       ├── crawl_log.parquet              # ghi bởi crawler/job_crawler/extensions.py — xem 3.7
│       ├── pipeline_metrics.parquet
│       └── exchange_rate_snapshot.parquet
│
├── labeling/                              # OFFLINE — không đổi so với v1
│   ├── README.md
│   ├── ground_truth/
│   ├── llm_assisted_labeling.py
│   ├── evaluate.py
│   └── benchmark_results.md
│
├── dashboard/
│   ├── streamlit_app.py
│   ├── pages/
│   └── utils/db_connector.py
│
├── docs/
│   ├── architecture.md
│   ├── schema_mapping.md
│   ├── adding_new_source.md                # [ĐÃ SỬA] thêm checklist "ngưỡng tốt nghiệp field" — 3.3
│   └── data_retention_policy.md
│
├── logs/{crawler,pipeline}/
├── docker-compose.yml
├── Makefile
└── .github/workflows/
    ├── crawler_ci.yml
    ├── pipeline_ci.yml
    └── daily_run.yml
```

---

## 3. Giải thích các thay đổi so với v1 (chỉ phần đã đổi — phần còn lại xem lý do gốc ở `job_data_folder_structure.md` mục 3.1–3.9)

### 3.1 `SourceAdapter` — interface bắt buộc, thay cho if/else theo tên nguồn

```python
# pipeline/model/source_interface.py
class SourceAdapter(Protocol):
    def extract(self, batch_date: str) -> list[RawRecord]: ...
    def parse(self, raw: RawRecord) -> SourceNormalized: ...
```
`pipeline_steps/` chỉ gọi qua interface này, không bao giờ import trực tiếp `sources/itviec/` hay `sources/topcv/`. Thêm nguồn = viết 1 adapter mới + đăng ký `SOURCE_REGISTRY`, không sửa file nào trong `pipeline_steps/`.

### 3.2 `SOURCE_REGISTRY` — capability đã verify trên dữ liệu thật (không phải giả định)

```python
SOURCE_REGISTRY = {
    "itviec": {
        "requires_browser": True,
        "has_ajax_preview": True,           # list dùng /content?job_index=N khác URL detail đầy đủ
        "has_json_data_layer": True,        # data-jobs--save-data-layer-value — ưu tiên đọc trước HTML
        "provides_skill_tags": True,
        "skill_tag_structure": "flat",
        "salary_can_be_gated": True,        # "Sign in to view salary" — null hợp lệ, không phải lỗi
    },
    "topcv": {
        "requires_browser": False,
        "has_ajax_preview": False,
        "has_json_data_layer": False,
        "provides_skill_tags": True,        # div.required-tags — verify lại sau khi phát hiện đọc thiếu
        "skill_tag_structure": "grouped",   # 3 nhóm: industry / required / nice_to_have
        "salary_can_be_gated": False,
    },
}
```

### 3.3 `SourceNormalized` — 2 tầng field: core bắt buộc + `source_extra` mở

```python
class SalaryStatus(str, Enum):
    DISCLOSED = "disclosed"
    NEGOTIABLE = "negotiable"
    AUTH_GATED = "auth_gated"      # ITviec: có số thật nhưng giấu sau đăng nhập
    NOT_PROVIDED = "not_provided"

class SourceNormalized(BaseModel):
    # CORE — bắt buộc mọi nguồn map được
    job_id: str
    source: str
    url: str
    title: str
    company_name: str
    locations: list[str]               # luôn list, kể cả nguồn chỉ có 1 địa điểm
    description_raw: str
    posted_date: date
    salary_status: SalaryStatus
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    listing_position: Optional[int] = None

    # EXTENSION — field đặc thù nguồn, không ép chuẩn hoá ngay
    source_extra: dict[str, Any] = {}
```

**Ngưỡng tốt nghiệp field** (ghi bắt buộc vào `docs/adding_new_source.md`): 1 field trong `source_extra` chỉ lên core khi **≥2 nguồn cùng cung cấp** + **có nhu cầu dashboard/lọc thật**. Ứng viên hiện tại đang chờ đủ điều kiện: `work_mode` (đã xác nhận cả 2 nguồn đều có, dạng khác nhau: ITviec badge tường minh, TopCV field `Hình thức làm việc` trong "Thông tin chung") và `experience_years_min` (TopCV structured, ITviec cần regex fallback từ mô tả — chấp nhận `None` phổ biến hơn).

### 3.4 `extract.py` — ưu tiên JSON data-layer trước CSS selector khi nguồn có sẵn

Với `has_json_data_layer=True` (ITviec), `sources/itviec/extract.py` đọc JSON trong `data-jobs--save-data-layer-value` trước — ổn định hơn CSS class khi site đổi giao diện. HTML parsing chỉ dùng cho field JSON không có (`company_type`, `company_size`, benefit bullets, mô tả đầy đủ). Nguyên tắc tổng quát cho nguồn tương lai: **luôn kiểm tra DOM có data-layer/JSON-LD nhúng sẵn trước khi viết selector**, vì nhiều site hiện đại (React/Stimulus) nhúng structured data cho analytics nội bộ, ổn định hơn class CSS.

### 3.5 `skill_extractor.py` — rẽ nhánh theo cấu trúc, không rẽ theo có/không

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
Cả 2 nguồn hiện tại đều cung cấp skill sẵn — NLP (`FlashText`) chỉ là fallback cho nguồn không có gì tương tự, không phải đường chính như giả định ban đầu.

**[Sửa]** `vocab_gap_logger.py` phải hook vào bước canonical hoá (`skills_taxonomy.py`), áp dụng cho candidate từ **cả 2 nhánh** — kể cả tag nguồn cung cấp sẵn (nhánh `flat`/`grouped`) không match được taxonomy cũng phải log, không chỉ log candidate từ FlashText/free-text. Lý do: taxonomy thiếu entry là tín hiệu cần cập nhật dù candidate đến từ đâu.

### 3.6 Contract test — bắt buộc pass trước khi merge adapter mới

```python
# pipeline/tests/contract/test_source_adapter_contract.py
@pytest.mark.parametrize("source_name", SOURCE_REGISTRY.keys())
def test_adapter_conforms(source_name):
    adapter = load_adapter(source_name)
    sample = adapter.parse(load_fixture(source_name, "case_a_full"))
    assert isinstance(sample, SourceNormalized)
    assert sample.locations and isinstance(sample.locations, list)
    assert sample.salary_status in SalaryStatus
    assert sample.description_raw.strip() != ""
    assert set(sample.model_fields) == CORE_FIELD_NAMES   # field lạ phải nằm trong source_extra
```
Đây là bài test duy nhất bắt buộc viết mới khi thêm nguồn — pass được thì toàn bộ `pipeline_steps/` phía sau tự động chạy đúng.

### 3.7 [MỚI] Crawler — đồng bộ với `crawler_design_final.md`

- **2 spider/nguồn** (listing + detail), join theo **`job_id`** — không phải `url`, vì URL có query string tracking đổi mỗi lần crawl (thấy rõ ở TopCV: `?ta_source=...&u_sr_id=...`).
- `items.py` bổ sung `job_id` (bắt buộc), `listing_page_num`, `listing_position` (nullable, chỉ có ở listing item) — mapping 1:1 sang `pipeline/model/raw_record.py`, `RawRecord` vẫn là nguồn sự thật (Pydantic validate), `items.py` chỉ là hộp chứa tối thiểu.
- `extensions.py` (mới) — hook `spider_closed` signal, ghi 1 dòng vào `data/metadata/crawl_log.parquet`/lần chạy spider (không phải 1 dòng/job): `run_id`, `source`, `spider_type`, `batch_date`, `jobs_found`, `jobs_failed`, `status`.
- `settings.py` cần khai báo `ROBOTSTXT_OBEY=True`, `AUTOTHROTTLE_ENABLED=True`, `DOWNLOAD_DELAY` riêng theo nguồn (TopCV 2–3s, ITviec 3–5s vì Playwright render tốn tài nguyên hơn) — chưa từng quyết định trước bản `crawler_design_final.md`.
- `batch_date` quy ước: luôn là ngày UTC lúc `daily_run.yml` bắt đầu chạy, set 1 lần ở bước đầu workflow, truyền xuống mọi spider qua `-a batch_date=$BATCH_DATE` — không để spider tự gọi `datetime.now()` riêng lẻ.

---

## 4. Bảng field — trạng thái hiện tại (core / ứng viên / extension-only)

| Field | Trạng thái | Ghi chú |
|---|---|---|
| `title`, `company_name`, `url`, `description_raw` | Core, chắc chắn | Duy nhất 4 field chắc chắn có ở mọi nguồn |
| `locations`, `posted_date`, `salary_status`, `listing_position` | Core, đã verify 2 nguồn | Khác dạng nhưng map được |
| `work_mode`, `experience_years_min` | **Ứng viên core** | Đủ điều kiện ≥2 nguồn, chờ xác nhận độ phủ qua nhiều mẫu hơn (xem mục 6.A) |
| `application_deadline` (TopCV), `job_domain`/`company_type`/`overtime_policy` (ITviec), badge công ty (TopCV) | `source_extra` only | Chỉ 1 nguồn — chưa đủ điều kiện lên core |
| `competition_level` (TopCV) | **Nghi ngờ, chưa dùng** | Có thể là số cá nhân hoá theo tài khoản login, không phải thuộc tính tĩnh của job — cần xác nhận trước khi crawl |

---

## 5. [MỚI] Pipeline — trạng thái ổn định (chưa sẵn sàng code, chỉ mới khung sườn)

### ✅ Đã ổn định — có logic cụ thể, verify trên dữ liệu thật
- `model/source_interface.py` (`SourceAdapter`) — contract rõ ràng
- `model/source_normalized.py` (2 tầng core/`source_extra`) — verify trên HTML thật 2 nguồn
- `shared/source_registry.py` — capability đã verify, không phải giả định
- `tools/skill_extractor.py` — flow 2 nhánh + canonical hoá đã thiết kế (bao gồm fix `vocab_gap_logger.py` ở mục 3.5)
- `tests/contract/test_source_adapter_contract.py` — đủ chặn adapter mới sai schema

### 🔴 Chưa thiết kế — chỉ là tên file, chưa có logic

**Nghẽn nghiêm trọng nhất — `pipeline_steps/merge.py`:** chưa thiết kế cách join `jobs_meta_listing.jsonl` + `jobs_meta_detail_status.jsonl` (2 output riêng của crawler, join theo `job_id`) thành 1 `RawRecord` đầy đủ trước khi đưa vào `sources/{source}/parse.py`. Đây là điểm nối trực tiếp giữa crawler và pipeline — không thiết kế xong thì mọi bước phía sau (`shared_validate.py`, `cross_source_dedupe.py`, `shared_enrich.py`) không có input thật để chạy, dù đã có ý tưởng trên giấy.

| Module | Vấn đề cụ thể |
|---|---|
| `shared_validate.py` | Mới có 1 rule (salary null hợp lệ nếu `salary_can_be_gated`). Chưa có rule cho `title`/`company_name` rỗng, `url` sai format |
| `shared_clean.py`, `shared_normalize.py`, `shared_salary_convert.py` | Chưa thiết kế gì — chỉ tên file |
| `cross_source_dedupe.py` | MinHash chọn từ v1 nhưng chưa stress-test dữ liệu thật — câu hỏi D.12 (tỷ lệ trùng thực tế) vẫn treo, ảnh hưởng threshold similarity |
| `store/` | Chưa quyết cách ghi `jobs_current` vs `jobs_log` khi cùng `job_id` xuất hiện ở nhiều batch; `schema.sql` mới ghi chú cần version `source_extra` struct, chưa có cách làm cụ thể |
| `title_classifier.py`, `flag_extractor.py` | Chưa thiết kế gì |
| `orchestrator/run_pipeline.py` | Chưa quyết sequencing — step nào chặn step nào khi lỗi, retry ở đâu |

**Thứ tự đề xuất:** `merge.py` trước tiên — là điểm nghẽn thật (blocker), không phải lựa chọn tuỳ ý. Không có nó thì không thể test `shared_validate.py`/`cross_source_dedupe.py` bằng dữ liệu thật.

---

## 6. Câu hỏi mở — chờ phân tích thêm

*(Ghi lại nguyên trạng để tiếp tục phân tích ở lượt sau, chưa ảnh hưởng tới cấu trúc ở trên cho tới khi có câu trả lời)*

### A. Xác nhận cấu trúc field (cần crawl thêm mẫu, không chỉ 1 job/nguồn)
1. `work_mode` của TopCV — job Remote/Hybrid có ghi đúng nhãn `Hình thức làm việc` không, hay có job để trống?
2. `skill_tag_structure` của TopCV có luôn đủ 3 nhóm không, hay có job thiếu 1–2 nhóm?
3. `has_json_data_layer` của ITviec có ổn định qua nhiều job không, hay có job thiếu attribute này?
4. `salary_status = AUTH_GATED` chiếm tỷ lệ bao nhiêu % job ITviec — có đáng đầu tư crawl có đăng nhập?

### B. Field đặc thù nguồn — cần xác nhận trước khi đưa vào `source_extra`
5. Company badges của TopCV (Diamond/Pro/Verified) — gắn với công ty hay gắn với tin đăng cụ thể?
6. `overtime_policy`/`working_days` của ITviec — xuất hiện ở mọi job hay chỉ 1 số công ty tự nguyện điền?
7. `competition_level` của TopCV — chỉ ẩn khi chưa login, hay thực sự không tồn tại ở HTML public?

### C. Phạm vi mở rộng nguồn — quyết định mức độ tổng quát của `SourceAdapter`
8. Nguồn thứ 3 dự kiến là gì — site HTML thuần hay site có API/JSON response (cần mở interface `extract()` để nhận cả raw JSON, không chỉ HTML)?
9. Nguồn tương lai có cần đăng nhập để xem đủ dữ liệu không — nếu có, cần session/cookie management trong `crawler/`.
10. Có nguồn tiếng Anh/quốc tế không — ảnh hưởng `title_rules.py`/`skills_taxonomy.py` có cần tách theo ngôn ngữ.

### D. Vận hành / chất lượng dữ liệu
11. Tần suất đổi cấu trúc HTML của 2 site — có đáng ưu tiên JSON data-layer làm nguồn chính hơn CSS selector ngay từ đầu?
12. Trùng lặp cross-source thực tế nhiều tới đâu (đặc biệt job từ agency như "ITviec Recruitment Consulting") — ảnh hưởng độ ưu tiên đầu tư cho `cross_source_dedupe.py`.