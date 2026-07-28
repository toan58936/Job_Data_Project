import json
import sys
from pathlib import Path

from pipeline.pipeline_steps.merge import merge_raw_records
from pipeline.sources.itviec.parse import parse

BATCH_DATE = "2026-07-28"
SOURCE = "itviec"
PARSED_DIR = Path("data/parsed")

def main():
    print(f"[run_parse] Merging {SOURCE}/{BATCH_DATE}...")
    records = merge_raw_records(SOURCE, BATCH_DATE)
    print(f"[run_parse] {len(records)} RawRecords loaded")

    parsed = []
    errors = []

    for raw in records:
        try:
            result = parse(raw)
            parsed.append(result.model_dump())
        except Exception as e:
            errors.append({"job_id": raw.job_id, "error": str(e)})
            print(f"  ERROR on {raw.job_id}: {e}", file=sys.stderr)

    print(f"[run_parse] Parsed: {len(parsed)}, Errors: {len(errors)}")

    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PARSED_DIR / f"{SOURCE}_{BATCH_DATE}.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for item in parsed:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"[run_parse] Output: {out_path}")

    if errors:
        err_path = PARSED_DIR / f"{SOURCE}_{BATCH_DATE}_errors.jsonl"
        with open(err_path, "w", encoding="utf-8") as f:
            for err in errors:
                f.write(json.dumps(err, ensure_ascii=False) + "\n")
        print(f"[run_parse] Errors logged: {err_path}")

    # Spot-check the first parsed result
    if parsed:
        first = parsed[0]
        print(f"[run_parse] Sample record:")
        print(f"  title: {first['title']}")
        print(f"  company_name: {first['company_name']}")
        print(f"  locations: {first['locations']}")
        print(f"  work_mode: {first['work_mode']}")
        print(f"  salary_status: {first['salary_status']}")
        print(f"  source_extra keys: {list(first['source_extra'].keys())}")
        print(f"  skills count: {len(first['source_extra'].get('skills', []))}")

    return len(errors)


if __name__ == "__main__":
    sys.exit(main())