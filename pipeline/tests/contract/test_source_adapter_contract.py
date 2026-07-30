import importlib.util
import json
import sys
from pathlib import Path

import pytest

from pipeline.model.raw_record import RawRecord
from pipeline.model.source_normalized import SalaryStatus, SourceNormalized
from shared.source_registry import SOURCE_REGISTRY
from shared.utils import safe_id

PIPELINE_DIR = Path(__file__).resolve().parent.parent.parent


def load_adapter(source_name: str):
    module_path = PIPELINE_DIR / "sources" / source_name / "parse.py"
    spec = importlib.util.spec_from_file_location(f"sources.{source_name}.parse", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"sources.{source_name}.parse"] = module
    spec.loader.exec_module(module)
    return module


def load_fixture(source_name: str, case_name: str) -> RawRecord:
    if source_name == "topcv" and case_name == "case_a_full":
        batch_dir = Path("data/raw/topcv/2026-07-28")
        listing_rows = []
        detail_rows = []
        with open(batch_dir / "jobs_meta_listing.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if row.get("job_id") == "1055808":
                    listing_rows.append(row)
        with open(batch_dir / "jobs_meta_detail_status.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if row.get("job_id") == "1055808":
                    detail_rows.append(row)
        listing_row = listing_rows[0] if listing_rows else {}
        detail_row = detail_rows[0] if detail_rows else None
    elif source_name == "itviec" and case_name == "case_a_full":
        batch_dir = Path("data/raw/itviec/2026-07-28")
        listing_rows = []
        detail_rows = []
        with open(batch_dir / "jobs_meta_listing.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if row.get("job_id") == "13-chuyen-gia-khoa-hoc-du-lieu-trung-tam-thong-tin-tin-dung-quoc-gia-viet-nam-cic-5606":
                    listing_rows.append(row)
        with open(batch_dir / "jobs_meta_detail_status.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if row.get("job_id") == "13-chuyen-gia-khoa-hoc-du-lieu-trung-tam-thong-tin-tin-dung-quoc-gia-viet-nam-cic-5606":
                    detail_rows.append(row)
        listing_row = listing_rows[0] if listing_rows else {}
        detail_row = detail_rows[0] if detail_rows else None
    else:
        raise ValueError(f"Unknown fixture: {source_name}/{case_name}")

    def _read_html(path: Path) -> str | None:
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    target_id = listing_row.get("job_id", "")
    html_slug = safe_id(target_id)
    listing_html_path = batch_dir / "raw_html" / "listing" / f"{html_slug}.html"
    detail_html_path = batch_dir / "raw_html" / "job_detail" / f"{html_slug}.html"

    return RawRecord(
        job_id=target_id,
        source=source_name,
        batch_date="2026-07-28",
        url=listing_row.get("url", ""),
        title_listing=listing_row.get("title", ""),
        listing_page_num=listing_row.get("listing_page_num"),
        listing_position=listing_row.get("listing_position"),
        raw_html_listing=_read_html(listing_html_path),
        detail_crawled=detail_row is not None,
        title_detail=detail_row.get("title") if detail_row else None,
        raw_html_detail=_read_html(detail_html_path) if detail_row else None,
    )


CORE_FIELD_NAMES = {
    "job_id",
    "source",
    "url",
    "title",
    "company_name",
    "locations",
    "description_raw",
    "posted_date_raw",
    "salary_status",
    "salary_min",
    "salary_max",
    "work_mode",
    "listing_position",
    "source_extra",
}


@pytest.mark.parametrize("source_name", SOURCE_REGISTRY.keys())
def test_adapter_conforms(source_name):
    adapter = load_adapter(source_name)
    sample = adapter.parse(load_fixture(source_name, "case_a_full"))
    assert isinstance(sample, SourceNormalized)
    assert sample.locations and isinstance(sample.locations, list)
    assert sample.salary_status in SalaryStatus
    assert sample.description_raw.strip() != ""
    assert set(SourceNormalized.model_fields) == CORE_FIELD_NAMES
