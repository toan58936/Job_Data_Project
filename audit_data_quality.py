import json
import os
import glob
from collections import defaultdict

def read_jsonl(filepath):
    records = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records

def read_parquet(filepath):
    try:
        import pandas as pd
        df = pd.read_parquet(filepath)
        return df.to_dict('records')
    except ImportError:
        print(f"Cannot read {filepath} because pandas/pyarrow is not installed.")
        return []

def _is_empty(val):
    """Kiểm tra giá trị rỗng, hỗ trợ cả numpy array (từ parquet)."""
    if val is None:
        return True
    if hasattr(val, "size"):  # numpy array
        return val.size == 0
    return val == "" or val == [] or val == ()

def main():
    print("--- STARTING DATA QUALITY AUDIT ---")
    
    # 1. COMPLETENESS
    clean_dir = r"e:\job-data-project\data\clean\year=2026\month=08"
    clean_files = glob.glob(os.path.join(clean_dir, "*.parquet"))
    clean_records = []
    for f in clean_files:
        clean_records.extend(read_parquet(f))
        
    total_gold = len(clean_records)
    print(f"\n### 1. COMPLETENESS")
    print(f"Total records in Gold layer: {total_gold}")
    
    fields_to_check = ['title', 'company_name', 'locations', 'work_mode']
    null_counts = {f: 0 for f in fields_to_check}
    skills_empty = 0

    for r in clean_records:
        for f in fields_to_check:
            val = r.get(f)
            if _is_empty(val):
                null_counts[f] += 1
                
        skills = r.get('job_skills')
        if _is_empty(skills):
            skills_empty += 1
            
    print("Completeness metrics:")
    for f in fields_to_check:
        pct = (null_counts[f] / total_gold * 100) if total_gold > 0 else 0
        print(f" - {f}: {pct:.2f}% null/empty ({null_counts[f]} records)")
        if pct > 5.0:
            print(f"   => FLAG: {f} exceeds 5% null/empty threshold!")
            
    skills_pct = (skills_empty / total_gold * 100) if total_gold > 0 else 0
    print(f" - job_skills: {skills_pct:.2f}% empty ({skills_empty} records)")
    if skills_pct > 10.0:
        print(f"   => FLAG: job_skills exceeds 10% empty threshold!")
        
    # 2. CONSISTENCY
    print(f"\n### 2. CONSISTENCY")
    locations_set = set()
    salary_status_set = set()
    salary_inconsistent = 0
    
    for r in clean_records:
        locs = r.get('locations', [])
        # Xử lý cả list Python và numpy array (từ parquet)
        if hasattr(locs, '__iter__'):
            for loc in locs:
                if loc:
                    locations_set.add(str(loc))
        elif isinstance(locs, str):
            locations_set.add(locs)
            
        sal_status = r.get('salary_status')
        if sal_status:
            salary_status_set.add(sal_status)
            
        if sal_status == 'disclosed':
            s_min = r.get('salary_min')
            s_max = r.get('salary_max')
            if s_min is None or s_max is None or not (isinstance(s_min, (int, float)) and isinstance(s_max, (int, float))):
                salary_inconsistent += 1

    print("Unique locations:")
    for loc in sorted(locations_set):
        flag = ""
        if loc in ['Hanoi', 'HCM', 'Ho Chi Minh']:
            flag = " => FLAG: Not properly normalized!"
        print(f" - {loc}{flag}")
        
    print(f"\nUnique salary_status values: {salary_status_set}")
    print(f"Records with 'disclosed' status but invalid min/max salary: {salary_inconsistent}")
    
    # 3. UNIQUENESS
    print(f"\n### 3. UNIQUENESS")
    enriched_itviec = read_jsonl(r"e:\job-data-project\data\enriched\itviec\2026-08-01\enriched.jsonl")
    enriched_topcv = read_jsonl(r"e:\job-data-project\data\enriched\topcv\2026-08-01\enriched.jsonl")
    total_enriched = len(enriched_itviec) + len(enriched_topcv)
    
    print(f"Total records in enriched layer (before dedup): {total_enriched}")
    print(f"Total records in clean layer (after dedup): {total_gold}")
    print(f"Jobs removed by deduplication: {total_enriched - total_gold}")
    
    # Randomly sample 3 pairs of jobs that share the same company_name and similar titles
    company_jobs = defaultdict(list)
    for r in clean_records:
        company_jobs[r.get('company_name')].append(r)
        
    pairs_found = 0
    print("\nSample pairs with same company and similar titles (manually verify):")
    for company, jobs in company_jobs.items():
        if len(jobs) > 1 and company:
            # just pick the first two for a simple sample
            print(f"Pair {pairs_found+1}:")
            print(f"  Job A: {jobs[0].get('title')} (ID: {jobs[0].get('job_id')})")
            print(f"  Job B: {jobs[1].get('title')} (ID: {jobs[1].get('job_id')})")
            pairs_found += 1
            if pairs_found >= 3:
                break
                
    # 4. ANOMALIES
    print(f"\n### 4. ANOMALIES")
    anomalies = []
    
    for r in clean_records:
        j_id = r.get('job_id')
        title = r.get('title')
        s_min = r.get('salary_min')
        s_max = r.get('salary_max')
        p_date = r.get('posted_date')
        
        # Salary outliers
        if s_min is not None and isinstance(s_min, (int, float)):
            if s_min > 200000000:
                anomalies.append((j_id, title, f"salary_min too high: {s_min}"))
            elif s_min < 1000000 and r.get('work_mode') == 'full-time':
                anomalies.append((j_id, title, f"salary_min too low for full-time: {s_min}"))
                
        if s_max is not None and isinstance(s_max, (int, float)):
            if s_max > 200000000:
                anomalies.append((j_id, title, f"salary_max too high: {s_max}"))
                
        # Date outliers
        if p_date:
            # Simple string comparison works for YYYY-MM-DD
            if p_date > "2026-08-03":
                anomalies.append((j_id, title, f"posted_date in future: {p_date}"))
            elif p_date < "2025-01-01":
                anomalies.append((j_id, title, f"posted_date too old: {p_date}"))
                
    print(f"Total anomalies found: {len(anomalies)}")
    for a in anomalies:
        print(f" - ID: {a[0]} | Title: {a[1]} | Anomaly: {a[2]}")
        
    print("\n--- END OF AUDIT ---")

if __name__ == "__main__":
    main()
