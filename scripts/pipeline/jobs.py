import pandas as pd
from jobspy import scrape_jobs

from pipeline.constants import (
    JOBS_HOURS_OLD,
    JOBS_RESULTS_PER_TERM,
    JOBS_SEARCH_TERMS,
)

_JOB_COLUMN_MAP: dict[str, str] = {
    "title": "job_title",
    "company": "company_name_raw",
    "min_amount": "salary_min",
    "max_amount": "salary_max",
    "is_remote": "is_remote",
    "description": "description",
}


def _scrape_term(search_term: str) -> pd.DataFrame:
    try:
        return scrape_jobs(
            site_name=["indeed", "linkedin"],
            search_term=search_term,
            location="United Kingdom",
            results_wanted=JOBS_RESULTS_PER_TERM,
            hours_old=JOBS_HOURS_OLD,
            country_indeed="UK",
            linkedin_fetch_description=True,
        )
    except Exception as e:
        print(f"  Warning: failed to scrape '{search_term}': {e}")
        return pd.DataFrame()


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    available = {k: v for k, v in _JOB_COLUMN_MAP.items() if k in df.columns}
    result = df[list(available.keys())].rename(columns=available).copy()

    result["company_name_normalized"] = (
        result["company_name_raw"].str.upper().str.strip().fillna("")
    )
    result["is_remote"] = result.get("is_remote", pd.Series(False)).fillna(False).astype(bool)

    if "salary_min" in result.columns:
        result["salary_min"] = pd.to_numeric(result["salary_min"], errors="coerce")
    if "salary_max" in result.columns:
        result["salary_max"] = pd.to_numeric(result["salary_max"], errors="coerce")

    return result


def scrape_all_jobs() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    for term in JOBS_SEARCH_TERMS:
        print(f"  Scraping: '{term}'...")
        df = _scrape_term(term)
        if not df.empty:
            frames.append(df)
            print(f"    Found {len(df)} jobs")

    if not frames:
        raise RuntimeError("No jobs scraped — check network connection")

    combined = pd.concat(frames, ignore_index=True)
    normalized = _normalize(combined)

    result = normalized.drop_duplicates(subset=["company_name_normalized", "job_title"])
    print(f"  Total unique jobs: {len(result):,}")
    return result
