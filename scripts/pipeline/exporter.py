from datetime import datetime
from pathlib import Path

import pandas as pd

from pipeline.constants import OUTPUT_DIR


def _dated_filename(ext: str) -> str:
    date_str = datetime.now().strftime("%Y%m%d")
    return f"uk_b2b_{date_str}.{ext}"


def save_csv(df: pd.DataFrame) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / _dated_filename("csv")
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  CSV saved:     {path}  ({len(df):,} rows)")
    return path


def save_parquet(df: pd.DataFrame) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / _dated_filename("parquet")
    df.to_parquet(path, index=False, engine="pyarrow")
    print(f"  Parquet saved: {path}  ({len(df):,} rows)")
    return path


def export(df: pd.DataFrame) -> tuple[Path, Path]:
    csv_path = save_csv(df)
    parquet_path = save_parquet(df)
    return csv_path, parquet_path
