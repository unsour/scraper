import json
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from jobspy import scrape_jobs
from loguru import logger

load_dotenv()

RAW_DIR = Path("/app/output/raw")
OUT_PATH = RAW_DIR / "jobs_raw.jsonl"

RESULTS_PER_TERM = 100
HOURS_OLD = 168  # 1 week

KEEP_COLUMNS = [
    "title", "company", "min_amount", "max_amount",
    "is_remote", "description", "location",
]


def _load_terms() -> list[str]:
    raw = os.getenv("JOBS_SEARCH_TERMS", "software engineer,data engineer,product manager")
    terms = [t.strip() for t in raw.split(",") if t.strip()]
    if not terms:
        raise RuntimeError("JOBS_SEARCH_TERMS is empty")
    return terms


def _scrape_term(term: str) -> pd.DataFrame:
    try:
        df = scrape_jobs(
            site_name=["linkedin", "indeed"],
            search_term=term,
            location="United Kingdom",
            results_wanted=RESULTS_PER_TERM,
            hours_old=HOURS_OLD,
            country_indeed="UK",
            linkedin_fetch_description=True,
        )
        logger.info(f"  '{term}' → {len(df)} jobs")
        return df
    except Exception as exc:
        logger.warning(f"  '{term}' failed: {exc}")
        return pd.DataFrame()


def _to_record(row: pd.Series) -> dict:
    return {
        "job_title": str(row.get("title") or ""),
        "company_name_raw": str(row.get("company") or ""),
        "salary_min": row.get("min_amount"),
        "salary_max": row.get("max_amount"),
        "is_remote": bool(row.get("is_remote") or False),
        "description": str(row.get("description") or ""),
        "location": str(row.get("location") or ""),
    }


def main() -> None:
    logger.info("=== 02_scrape_jobs.py ===")
    terms = _load_terms()
    logger.info(f"Search terms: {terms}")

    frames: list[pd.DataFrame] = []
    for term in terms:
        df = _scrape_term(term)
        if not df.empty:
            frames.append(df)

    if not frames:
        raise RuntimeError("No jobs scraped — check network or API keys")

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(subset=["company", "title"])

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for _, row in combined.iterrows():
            record = _to_record(row)
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    logger.success(f"Saved {len(combined):,} jobs → {OUT_PATH}")


if __name__ == "__main__":
    main()
