import json
from pathlib import Path

import duckdb
import pandas as pd
from loguru import logger
from rapidfuzz import fuzz, process

FUZZY_THRESHOLD = 88.0
CH_PATH = Path("/app/output/raw/ch_basic.csv")
JOBS_PATH = Path("/app/output/raw/jobs_raw.jsonl")
DB_PATH = Path("/app/output/merged/merged.duckdb")


def _normalize(name: str) -> str:
    return str(name).upper().strip()


def _load_jobs() -> pd.DataFrame:
    records: list[dict] = []
    with open(JOBS_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    df = pd.DataFrame(records)
    df["name_normalized"] = df["company_name_raw"].apply(_normalize)
    return df


def _load_companies() -> pd.DataFrame:
    df = pd.read_csv(CH_PATH)
    df["name_normalized"] = df["company_name"].apply(_normalize)
    return df.drop_duplicates(subset=["name_normalized"])


def _exact_join(jobs: pd.DataFrame, ch: pd.DataFrame) -> pd.DataFrame:
    ch_slim = ch[["name_normalized", "company_number", "sic_description", "city", "incorporation_date"]]
    merged = jobs.merge(ch_slim, on="name_normalized", how="inner")
    return merged.assign(match_type="exact", match_score=1.0)


def _fuzzy_join(unmatched: pd.DataFrame, ch: pd.DataFrame) -> pd.DataFrame:
    ch_names = ch["name_normalized"].tolist()
    ch_index = ch.set_index("name_normalized")
    rows: list[dict] = []

    for _, job_row in unmatched.iterrows():
        result = process.extractOne(
            job_row["name_normalized"],
            ch_names,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=FUZZY_THRESHOLD,
        )
        if result is None:
            continue

        matched_name, score, _ = result
        ch_row = ch_index.loc[matched_name]
        rows.append({
            **job_row.to_dict(),
            "company_number": ch_row["company_number"],
            "sic_description": ch_row["sic_description"],
            "city": ch_row["city"],
            "incorporation_date": ch_row["incorporation_date"],
            "match_type": "fuzzy",
            "match_score": round(score / 100.0, 4),
        })

    return pd.DataFrame(rows)


def main() -> None:
    logger.info("=== 03_merge.py ===")

    logger.info("Loading companies and jobs...")
    ch = _load_companies()
    jobs = _load_jobs()
    logger.info(f"  CH: {len(ch):,}  |  Jobs: {len(jobs):,}")

    exact = _exact_join(jobs, ch)
    logger.info(f"  Exact matches: {len(exact):,}")

    matched_names = set(exact["name_normalized"].unique())
    unmatched = jobs[~jobs["name_normalized"].isin(matched_names)]

    fuzzy = pd.DataFrame()
    if not unmatched.empty:
        logger.info(f"  Running fuzzy match on {len(unmatched):,} unmatched jobs...")
        fuzzy = _fuzzy_join(unmatched, ch)
        logger.info(f"  Fuzzy matches: {len(fuzzy):,}")

    frames = [exact] + ([fuzzy] if not fuzzy.empty else [])
    merged = pd.concat(frames, ignore_index=True)
    logger.info(f"  Total merged: {len(merged):,}")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(DB_PATH))
    conn.register("merged_df", merged)
    conn.execute("CREATE OR REPLACE TABLE merged AS SELECT * FROM merged_df")
    conn.close()

    logger.success(f"Saved merged table → {DB_PATH}")


if __name__ == "__main__":
    main()
