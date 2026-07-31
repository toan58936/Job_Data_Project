# Job Data Project — Cấu trúc dự án chuẩn (v5 — cập nhật theo dữ liệu detail thật)

> Bản này hợp nhất `job_data_folder_structure.md` (v1 — cây thư mục gốc), phần source-abstraction đã verify trên HTML thật (mục 1–6), `crawler_design_final.md` (kiến trúc crawl đã chốt), bản đánh giá độ ổn định pipeline (mục 5), và **2 file detail thật vừa verify** (ITviec + TopCV — xác nhận `work_mode` tốt nghiệp lên core, TopCV skill không luôn đủ 3 nhóm, sửa `requires_browser` TopCV theo bằng chứng crawl thật, đồng bộ việc xoá `extensions.py` dead code). Từ nay đây là bản tham chiếu chính.
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
│   │   └── settings.py                    # DOWNLOAD_DELAY, AUTOTHROTTLE, ROBOTSTXT_OBEY — xem 3.7
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
│   │   │   └── parse.py                   # [ĐÃ ĐỔI] không còn extract.py riêng — logic ưu tiên
│   │   │                                  # đọc JSON data-layer trước HTML giờ nằm ngay trong
│   │   │                                  # parse.py (nhận raw_html_detail đã có sẵn từ merge.py,
│   │   │                                  # tự quyết định đọc JSON hay CSS selector) — xem 3.4
│   │   └── topcv/
│   │       └── parse.py                   # skill_tag_structure="grouped" — tách 3 nhóm skill,
│   │                                      # tolerant nếu thiếu nhóm (verify job_id=1055808 thật)
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
│       ├── crawl_log.parquet              # [SỬA] ghi bởi base_spider.py._on_spider_closed
│       │                                  # (extensions.py là dead code, đã xoá thật khỏi repo)
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
    def parse(self, raw: RawRecord) -> SourceNormalized: ...
```

**[ĐÃ ĐỔI]** Bản trước có cả `extract()` lẫn `parse()` trong contract. Sau khi viết `pipeline_steps/merge.py` thật, `extract()` không cần khai báo riêng theo từng nguồn nữa — `merge.py` đọc `jobs_meta_listing.jsonl`/`jobs_meta_detail_status.jsonl`/file `.html` theo cách hoàn toàn source-agnostic (không cần biết gì về ITviec/TopCV cụ thể), cho ra `RawRecord` chung cho mọi nguồn. Việc "extract" thực chất đã là bước dùng chung, không phải đặc thù từng nguồn — nên bỏ khỏi contract, chỉ giữ `parse()`.
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
        "requires_browser": True,           # [SỬA — evidence: crawl thật] KHÔNG phải suy từ đọc HTML
                                             # tĩnh (mẫu tĩnh không có dấu hiệu chặn bot) — phát hiện
                                             # qua crawl thật: Cloudflare trả 403 với request thường,
                                             # phải bật scrapy-playwright mới qua được. Ví dụ cụ thể
                                             # nguyên tắc 6: registry phải sửa theo bằng chứng vận hành
                                             # thật, không chỉ theo phân tích HTML tĩnh.
        "has_ajax_preview": False,
        "has_json_data_layer": False,
        "provides_skill_tags": True,        # div.required-tags — verify đúng là skill, không phải benefit
        "skill_tag_structure": "grouped",   # 3 nhóm: industry / required / nice_to_have
                                             # [MỚI] KHÔNG phải job nào cũng có đủ 3 nhóm — verify trên
                                             # job_id=1055808 thật: chỉ có "Kỹ năng cần có", thiếu 2 nhóm
                                             # còn lại. parse.py phải tolerant, không giả định đủ 3.
        "salary_can_be_gated": False,
    },
}
```

**[MỚI] Cấu trúc nhãn skill ITviec — xác nhận bằng HTML thật, không có class CSS phân biệt nhóm:** verify trên file detail thật (`13-chuyen-gia-khoa-hoc-du-lieu-...cic-5606.html`) — nhãn text `"Skills:"` đứng ngay trước nhóm thẻ `<a class="itag">`, nhãn `"Job Expertise"` đứng ngay sau nhóm đó, cả 2 nhóm thẻ dùng chung 1 class CSS. `sources/itviec/parse.py` bắt buộc phải là 1 state machine duyệt DOM theo thứ tự, gán bucket theo text nhãn đứng trước — không thể lọc bằng CSS selector đơn thuần.

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
    work_mode: Optional[str] = None    # [MỚI — tốt nghiệp lên core] "onsite" | "hybrid" | "remote" | None
                                        # Evidence: verify trên 2 file detail thật — ITviec "At office",
                                        # TopCV "Làm việc tại văn phòng / Onsite". Cần map giá trị gốc
                                        # của từng nguồn về 3 giá trị chuẩn này trong parse.py.

    # EXTENSION — field đặc thù nguồn, không ép chuẩn hoá ngay
    source_extra: dict[str, Any] = {}
```

**Ngưỡng tốt nghiệp field** (ghi bắt buộc vào `docs/adding_new_source.md`): 1 field trong `source_extra` chỉ lên core khi **≥2 nguồn cùng cung cấp** + **có nhu cầu dashboard/lọc thật**. `work_mode` vừa tốt nghiệp (mục trên). Ứng viên còn lại: `experience_years_min` (TopCV structured, ITviec cần regex fallback từ mô tả — chấp nhận `None` phổ biến hơn, chưa đủ bằng chứng thật để tốt nghiệp).

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

**[Xác nhận bằng dữ liệu thật]** Nhánh `grouped` dùng `.get(..., [])` nên đã tolerant sẵn với case TopCV thiếu nhóm — verify trên `job_id=1055808` thật: chỉ có `"Kỹ năng cần có"`, không có `"Kiến thức ngành"`/`"Kỹ năng nên có"`, hàm vẫn chạy đúng, `skills_nice_to_have=[]` thay vì lỗi. Không cần sửa logic, chỉ cần lưu ý khi viết `parse.py` không được raise lỗi nếu thiếu 1-2 nhóm.

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
- **[SỬA]** `crawl_log.parquet` ghi bởi `base_spider.py._on_spider_closed` (hook `spider_closed` signal) — **không phải** `extensions.py` như bản trước ghi (file đó là dead code, đã xoá thật khỏi repo, logic trùng lặp gây nhầm lẫn nơi nào đang chạy thật). `jobs_failed` đếm qua `stats.get(f"downloader/response_status_count/{code}")` cộng dồn theo `handle_httpstatus_list`, **không** đếm qua exception count — vì Cloudflare 403/429/500... được khai trong `handle_httpstatus_list` để không raise exception, nên đếm theo exception sẽ luôn ra 0 dù crawl fail hàng loạt thật (bug đã sửa, verify bằng code).
- **[SỬA]** Selector title ở cả 2 detail spider từng có bug nested-tag (title nằm trong `<span>`/`<a>` lồng bên trong `h1`, `::text` chỉ lấy text node trực tiếp nên trả rỗng) — sửa bằng `xpath("string(.)")` để gom toàn bộ text con cháu, đã verify đúng trên 2 file detail thật (ITviec, TopCV).
- `settings.py` cần khai báo `ROBOTSTXT_OBEY=True`, `AUTOTHROTTLE_ENABLED=True`, `DOWNLOAD_DELAY` riêng theo nguồn (TopCV 2–3s, ITviec 3–5s vì Playwright render tốn tài nguyên hơn) — chưa từng quyết định trước bản `crawler_design_final.md`.
- `batch_date` quy ước: luôn là ngày UTC lúc `daily_run.yml` bắt đầu chạy, set 1 lần ở bước đầu workflow, truyền xuống mọi spider qua `-a batch_date=$BATCH_DATE` — không để spider tự gọi `datetime.now()` riêng lẻ.

---

## 4. Bảng field (core / ứng viên / extension-only)

| Field | Trạng thái | Ghi chú |
|---|---|---|
| `title`, `company_name`, `url`, `description_raw` | Core, chắc chắn | Duy nhất 4 field chắc chắn có ở mọi nguồn |
| `locations`, `posted_date`, `salary_status`, `listing_position`, `work_mode` | Core, đã verify 2 nguồn | `work_mode` mới tốt nghiệp — evidence: ITviec "At office", TopCV "Onsite" trên file detail thật |
| `experience_years_min` | **Ứng viên core** | TopCV structured, ITviec cần regex fallback — chưa đủ bằng chứng thật để tốt nghiệp |
| `application_deadline` (TopCV), `job_domain`/`company_type`/`overtime_policy` (ITviec), badge công ty (TopCV) | `source_extra` only | Chỉ 1 nguồn — chưa đủ điều kiện lên core |
| `competition_level` (TopCV) | **Nghi ngờ, chưa dùng** | Có thể là số cá nhân hoá theo tài khoản login, không phải thuộc tính tĩnh của job — cần xác nhận trước khi crawl |