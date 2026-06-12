import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import duckdb
import pandas as pd
from dotenv import load_dotenv
from loguru import logger
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

DB_PATH = Path("/app/output/merged/merged.duckdb")
LOG_PATH = Path("/app/output/logs/enrich.log")

LLM_BATCH_SIZE = int(os.getenv("LLM_BATCH_SIZE", "20"))
LLM_MAX_WORKERS = int(os.getenv("LLM_MAX_WORKERS", "1"))
FIREWORKS_BASE = "https://api.fireworks.ai/inference/v1"
DEFAULT_MODEL = "accounts/fireworks/models/deepseek-v3"

ENRICH_COLUMNS = [
    "industry_label", "company_size", "tech_stack",
    "hiring_velocity", "remote_friendly", "salary_range_gbp",
    "tags", "quality_score",
]


def _get_client() -> tuple[OpenAI, str]:
    api_key = os.getenv("FIREWORKS_API_KEY")
    if not api_key:
        raise RuntimeError("FIREWORKS_API_KEY not set in .env")
    model = os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL)
    return OpenAI(api_key=api_key, base_url=FIREWORKS_BASE), model


def _build_prompt(batch: list[dict]) -> str:
    return f"""Analyze these {len(batch)} UK companies. Return a JSON array of {len(batch)} objects.

{json.dumps(batch, ensure_ascii=False, indent=2)}

Each object must have:
{{"industry_label":"SaaS|FinTech|HealthTech|...","company_size":"startup|small|medium|large",
"tech_stack":"comma-separated","hiring_velocity":"low|medium|high","remote_friendly":true|false,
"salary_range_gbp":"40000-70000 or null","tags":"comma-separated b2b tags",
"quality_score":0-100}}

quality_score: 80-100 active tech, 60-79 good signals, 40-59 weak, <40 poor.
Return ONLY a JSON array. No markdown."""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10), reraise=True)
def _call_llm(client: OpenAI, model: str, prompt: str) -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=4096,
    )
    return resp.choices[0].message.content or ""


def _parse_response(text: str, expected: int) -> list[dict]:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    parsed = json.loads(text)
    if len(parsed) != expected:
        raise ValueError(f"Expected {expected} items, got {len(parsed)}")
    return parsed


def _process_batch(
    batch: list[dict],
    client: OpenAI,
    model: str,
    batch_num: int,
    total: int,
) -> list[dict]:
    logger.info(f"  Batch {batch_num}/{total} ({len(batch)} companies)...")
    try:
        raw = _call_llm(client, model, _build_prompt(batch))
        results = _parse_response(raw, len(batch))
        for i, row in enumerate(results):
            row["name_normalized"] = batch[i]["name_normalized"]
        return results
    except Exception as exc:
        logger.error(f"  Batch {batch_num} failed: {exc}")
        return [{"name_normalized": r["name_normalized"], **{c: None for c in ENRICH_COLUMNS}} for r in batch]


def _load_companies(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return conn.execute("""
        SELECT name_normalized,
               FIRST(company_name)       AS company_name,
               FIRST(sic_description)    AS sic_description,
               FIRST(city)               AS city,
               FIRST(incorporation_date) AS incorporation_date,
               string_agg(DISTINCT job_title, ', ') AS job_titles,
               BOOL_OR(is_remote)        AS has_remote,
               COUNT(*)                  AS job_count
        FROM merged GROUP BY name_normalized
    """).df()


def main() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger.add(str(LOG_PATH), rotation="10 MB", level="DEBUG")
    logger.info("=== 04_enrich.py ===")

    client, model = _get_client()
    logger.info(f"Model: {model}  |  batch_size: {LLM_BATCH_SIZE}  |  workers: {LLM_MAX_WORKERS}")

    conn = duckdb.connect(str(DB_PATH))
    companies = _load_companies(conn)
    logger.info(f"Companies to enrich: {len(companies):,}")

    batches = [
        companies.iloc[i: i + LLM_BATCH_SIZE].to_dict(orient="records")
        for i in range(0, len(companies), LLM_BATCH_SIZE)
    ]
    total = len(batches)
    all_results: list[dict] = []

    with ThreadPoolExecutor(max_workers=LLM_MAX_WORKERS) as pool:
        futures = {
            pool.submit(_process_batch, b, client, model, i + 1, total): i
            for i, b in enumerate(batches)
        }
        for future in as_completed(futures):
            all_results.extend(future.result())

    enriched_df = pd.DataFrame(all_results)
    conn.register("enriched_df", enriched_df)
    conn.execute("CREATE OR REPLACE TABLE enriched AS SELECT * FROM enriched_df")
    conn.close()
    logger.success(f"Enriched {len(enriched_df):,} companies → {DB_PATH}")


if __name__ == "__main__":
    main()
