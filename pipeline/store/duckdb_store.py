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