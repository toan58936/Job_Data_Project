import argparse
import json
import sys
from pathlib import Path

from pipeline.pipeline_steps.merge import merge_raw_records
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

    for source in sources:
        parse_fn = PARSERS[source]
        batch_date = args.batch_date
        print(f"[run_parse] Merging {source}/{batch_date}...")
        records = merge_raw_records(source, batch_date)
        print(f"[run_parse] {len(records)} RawRecords loaded")

        parsed = []
        errors = []

        for raw in records:
            try:
                result = parse_fn(raw)
                parsed.append(result.model_dump())
            except Exception as e:
                errors.append({"job_id": raw.job_id, "error": str(e)})
                print(f"  ERROR on {raw.job_id}: {e}", file=sys.stderr)

        print(f"[run_parse] Parsed: {len(parsed)}, Errors: {len(errors)}")

        PARSED_DIR.mkdir(parents=True, exist_ok=True)
        out_path = PARSED_DIR / f"{source}_{batch_date}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for item in parsed:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"[run_parse] Output: {out_path}")

        if errors:
            err_path = PARSED_DIR / f"{source}_{batch_date}_errors.jsonl"
            with open(err_path, "w", encoding="utf-8") as f:
                for err in errors:
                    f.write(json.dumps(err, ensure_ascii=False) + "\n")
            print(f"[run_parse] Errors logged: {err_path}")

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

        total_errors += len(errors)

    return total_errors


if __name__ == "__main__":
    sys.exit(main())