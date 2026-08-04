"""
duckdb_store.py — Bước 7: Tầng Lưu trữ (Lakehouse Storage Layer).
Chuyển đổi dữ liệu JobPosting sang định dạng Parquet với chiến lược
phân vùng (Partitioning) theo Year/Month.
Sẵn sàng cho DuckDB/Spark truy vấn phân tích trực tiếp.
"""
import json
from pathlib import Path
from typing import List

import pandas as pd

from pipeline.model.job_posting import JobPosting


def store_to_parquet(records: List[JobPosting], batch_date: str, data_root: Path = Path("data/clean")) -> Path:
    """
    Nhận mảng Dữ liệu Vàng đã Dedupe, ghi xuống thư mục data/clean/ dưới dạng Parquet.
    Partition folder: data/clean/year=YYYY/month=MM/jobs_YYYY-MM-DD.parquet
    """
    if not records:
        return None

    # 1. Chuyển đổi Pydantic Models sang List[Dict]
    data = [r.model_dump(exclude_none=True) for r in records]
    df = pd.DataFrame(data)

    # 2. Xử lý các kiểu dữ liệu phức tạp (Dict/List) để tương thích chuẩn Parquet
    if "source_extra" in df.columns:
        # Ép kiểu dictionary metadata thành JSON string để Parquet dễ lưu trữ
        df["source_extra"] = df["source_extra"].apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, dict) else x)
    
    if "locations" in df.columns:
        df["locations"] = df["locations"].apply(lambda x: list(x) if isinstance(x, list) else [])

# 3. Phân vùng vật lý (Partitioning by Date)
    year, month, _ = batch_date.split("-")
    partition_dir = data_root / f"year={year}" / f"month={month}"
    partition_dir.mkdir(parents=True, exist_ok=True)

    file_path = partition_dir / f"jobs_{records[0].source}_{batch_date}.parquet"

    # 4. Ghi file Parquet (sử dụng engine pyarrow)
    df.to_parquet(file_path, index=False, engine="pyarrow", compression="snappy")
    
    return file_path


# Các cột PHÂN TÍCH ĐƯỢC (analyzable) giữ lại trong Gold layer cho dashboard.
# LOẠI BỎ các cột vận hành/văn bản (operational/text) để Gold gọn, chỉ còn
# categorical/numeric/date. URL được bỏ ra khỏi Gold — để join ngược lên
# enriched layer truy vết, dùng cặp (job_id, source) làm khóa.
GOLD_ANALYZABLE_COLUMNS = [
    "job_id",
    "source",
    "title",
    "company_name",
    "locations",
    "work_mode",
    "job_role",
    "seniority_level",
    "job_skills",
    "salary_status",
    "salary_min",
    "salary_max",
    "salary_currency",
    "posted_date",
]


def store_to_gold(records: List[JobPosting], batch_date: str, data_root: Path = Path("data/gold")) -> Path:
    """
    Ghi Gold layer cho dashboard: chỉ giữ các cột phân tích được.
    Partition: data/gold/year=YYYY/month=MM/jobs_YYYY-MM-DD.parquet

    Khác với store_to_parquet (giữ toàn bộ, ghi theo source riêng), hàm này:
    - Gộp cross-source (records đã qua deduplicate).
    - Chỉ ghi GOLD_ANALYZABLE_COLUMNS (bỏ url, description_raw, source_extra,
      data_completeness, crawled_at, listing_position, job_expertise, job_domains).
    - (job_id, source) là khóa join để trace ngược về enriched layer.
    """
    if not records:
        return None

    data = [r.model_dump(exclude_none=True) for r in records]

    # Lọc cột: chỉ giữ các cột có trong GOLD_ANALYZABLE_COLUMNS mà record có.
    rows = []
    for item in data:
        rows.append({col: item.get(col) for col in GOLD_ANALYZABLE_COLUMNS if col in item})

    df = pd.DataFrame(rows)

    # Chuẩn hóa kiểu dữ liệu cho Parquet (list/dict)
    if "locations" in df.columns:
        df["locations"] = df["locations"].apply(lambda x: list(x) if isinstance(x, list) else [])
    if "job_skills" in df.columns:
        df["job_skills"] = df["job_skills"].apply(lambda x: list(x) if isinstance(x, list) else [])

    year, month, _ = batch_date.split("-")
    partition_dir = data_root / f"year={year}" / f"month={month}"
    partition_dir.mkdir(parents=True, exist_ok=True)

    file_path = partition_dir / f"jobs_{batch_date}.parquet"
    df.to_parquet(file_path, index=False, engine="pyarrow", compression="snappy")
    return file_path
