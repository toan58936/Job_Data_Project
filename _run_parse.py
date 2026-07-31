import argparse
import json
import sys
from pathlib import Path

from pipeline.pipeline_steps.merge import merge_raw_records
from pipeline.pipeline_steps.shared_enrich import enrich
from pipeline.sources.itviec.parse import parse as itviec_parse
from pipeline.sources.topcv.parse import parse as topcv_parse

PARSERS = {
    "itviec": itviec_parse,
    "topcv": topcv_parse,
}

PARSED_DIR = Path("data/parsed")


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["itviec", "topcv", "all"], default="all")
    parser.add_argument("--batch-date", required=True)
    args = parser.parse_args()

    sources = list(PARSERS.keys()) if args.source == "all" else [args.source]
    total_errors = 0

    PARSED_DIR.mkdir(parents=True, exist_ok=True)

    for source in sources:
        parse_fn = PARSERS[source]
        batch_date = args.batch_date
        print(f"[run_parse] Merging {source}/{batch_date}...")
        records = merge_raw_records(source, batch_date)
        print(f"[run_parse] {len(records)} RawRecords loaded")

        errors = []
        out_path = PARSED_DIR / f"{source}_{batch_date}.jsonl"
        
        parsed_count = 0
        first_record = None

        with open(out_path, "w", encoding="utf-8") as f:
            for raw in records:
                try:
                    result = parse_fn(raw)
                    result = enrich(result)
                    dumped = result.model_dump()
                    if parsed_count == 0:
                        first_record = dumped
                    f.write(json.dumps(dumped, ensure_ascii=False) + "\n")
                    parsed_count += 1
                except Exception as e:
                    errors.append({"job_id": raw.job_id, "error": str(e)})
                    print(f"  ERROR on {raw.job_id}: {e}", file=sys.stderr)

        print(f"[run_parse] Parsed: {parsed_count}, Errors: {len(errors)}")
        print(f"[run_parse] Output: {out_path}")

        if errors:
            err_path = PARSED_DIR / f"{source}_{batch_date}_errors.jsonl"
            with open(err_path, "w", encoding="utf-8") as f:
                for err in errors:
                    f.write(json.dumps(err, ensure_ascii=False) + "\n")
            print(f"[run_parse] Errors logged: {err_path}")

        if first_record:
            print(f"[run_parse] Sample record:")
            print(f"  title: {first_record['title']}")
            print(f"  company_name: {first_record['company_name']}")
            print(f"  locations: {first_record['locations']}")
            print(f"  work_mode: {first_record['work_mode']}")
            print(f"  salary_status: {first_record['salary_status']}")
            print(f"  source_extra keys: {list(first_record['source_extra'].keys())}")
            print(f"  skills count: {len(first_record['source_extra'].get('skills_all', []))}")

        total_errors += len(errors)

    return total_errors


if __name__ == "__main__":
    sys.exit(main())