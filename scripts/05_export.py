import os
from datetime import datetime
from pathlib import Path

import duckdb
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

DB_PATH = Path("/app/output/merged/merged.duckdb")
OUT_DIR = Path("/app/output/final")
MIN_SCORE = int(os.getenv("MIN_QUALITY_SCORE", "60"))

EXPORT_QUERY = """
SELECT
    m.company_name,
    m.company_number,
    m.sic_description,
    m.city,
    m.incorporation_date,
    m.job_title,
    m.salary_min,
    m.salary_max,
    m.is_remote,
    m.match_type,
    e.industry_label,
    e.company_size,
    e.tech_stack,
    e.hiring_velocity,
    e.remote_friendly,
    e.salary_range_gbp,
    e.tags,
    e.quality_score
FROM merged m
LEFT JOIN enriched e ON m.name_normalized = e.name_normalized
WHERE e.quality_score >= {min_score}
ORDER BY e.quality_score DESC
"""


def _dated_path(ext: str) -> Path:
    date_str = datetime.now().strftime("%Y%m%d")
    return OUT_DIR / f"uk_b2b_{date_str}.{ext}"


def main() -> None:
    logger.info("=== 05_export.py ===")
    logger.info(f"Min quality_score: {MIN_SCORE}")

    conn = duckdb.connect(str(DB_PATH), read_only=True)
    query = EXPORT_QUERY.format(min_score=MIN_SCORE)
    df = conn.execute(query).df()
    conn.close()

    logger.info(f"Rows passing filter: {len(df):,}")
    if df.empty:
        logger.warning("No rows meet quality threshold — lower MIN_QUALITY_SCORE?")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = _dated_path("csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    logger.success(f"CSV  → {csv_path}  ({csv_path.stat().st_size // 1024} KB)")

    parquet_path = _dated_path("parquet")
    df.to_parquet(parquet_path, index=False, engine="pyarrow")
    logger.success(f"Parquet → {parquet_path}  ({parquet_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
