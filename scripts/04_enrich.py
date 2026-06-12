import json
import os
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

FIREWORKS_BASE = "https://api.fireworks.ai/inference/v1"
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
FIREWORKS_MODEL = "accounts/fireworks/models/deepseek-v3"
OPENROUTER_MODEL = "deepseek/deepseek-chat"

ENRICH_COLUMNS = [
    "industry_label", "company_size", "tech_stack",
    "hiring_velocity", "remote_friendly", "salary_range_gbp",
    "tags", "quality_score",
]


def _get_client() -> tuple[OpenAI, str]:
    fw_key = os.getenv("FIREWORKS_API_KEY")
    or_key = os.getenv("OPENROUTER_API_KEY")

    if fw_key:
        return OpenAI(api_key=fw_key, base_url=FIREWORKS_BASE), FIREWORKS_MODEL
    if or_key:
        return OpenAI(api_key=or_key, base_url=OPENROUTER_BASE), OPENROUTER_MODEL
    raise RuntimeError("Set FIREWORKS_API_KEY or OPENROUTER_API_KEY in .env")


def _build_prompt(batch: list[dict]) -> str:
    companies_json = json.dumps(batch, ensure_ascii=False, indent=2)
    return f"""You are a B2B data analyst. Analyze these {len(batch)} UK companies and return enrichment.

{companies_json}

Return a JSON array of exactly {len(batch)} objects in the same order:
{{
  "industry_label": "SaaS|FinTech|HealthTech|E-commerce|Consulting|...",
  "company_size": "startup|small|medium|large",
  "tech_stack": "comma-separated technologies",
  "hiring_velocity": "low|medium|high",
  "remote_friendly": true|false,
  "salary_range_gbp": "40000-70000 or null",
  "tags": "comma-separated b2b tags",
  "quality_score": 0-100
}}

quality_score: 80-100 active tech company, 60-79 good signals, 40-59 weak, <40 poor.
Return ONLY a JSON array. No markdown, no explanation."""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10), reraise=True)
def _call_llm(client: OpenAI, model: str, prompt: str) -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=4096,
    )
    return resp.choices[0].message.content or ""


def _parse_response(text: str, batch_size: int) -> list[dict]:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]

    parsed = json.loads(text)
    if len(parsed) != batch_size:
        raise ValueError(f"Expected {batch_size} items, got {len(parsed)}")
    return parsed


def _load_companies(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return conn.execute("""
        SELECT
            name_normalized,
            FIRST(company_name) AS company_name,
            FIRST(sic_description) AS sic_description,
            FIRST(city) AS city,
            FIRST(incorporation_date) AS incorporation_date,
            string_agg(DISTINCT job_title, ', ') AS job_titles,
            BOOL_OR(is_remote) AS has_remote,
            COUNT(*) AS job_count
        FROM merged
        GROUP BY name_normalized
    """).df()


def main() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger.add(str(LOG_PATH), rotation="10 MB", level="DEBUG")
    logger.info("=== 04_enrich.py ===")

    client, model = _get_client()
    logger.info(f"Using model: {model}")

    conn = duckdb.connect(str(DB_PATH))
    companies = _load_companies(conn)
    logger.info(f"Companies to enrich: {len(companies):,}")

    all_results: list[dict] = []
    for i in range(0, len(companies), LLM_BATCH_SIZE):
        batch_df = companies.iloc[i : i + LLM_BATCH_SIZE]
        batch = batch_df.to_dict(orient="records")
        batch_num = i // LLM_BATCH_SIZE + 1
        total_batches = (len(companies) - 1) // LLM_BATCH_SIZE + 1
        logger.info(f"  Batch {batch_num}/{total_batches} ({len(batch)} companies)...")

        try:
            raw = _call_llm(client, model, _build_prompt(batch))
            results = _parse_response(raw, len(batch))
            for j, row in enumerate(results):
                row["name_normalized"] = batch[j]["name_normalized"]
            all_results.extend(results)
        except Exception as exc:
            logger.error(f"  Batch {batch_num} failed: {exc}")
            for row in batch:
                all_results.append({"name_normalized": row["name_normalized"], **{c: None for c in ENRICH_COLUMNS}})

    enriched_df = pd.DataFrame(all_results)
    conn.register("enriched_df", enriched_df)
    conn.execute("CREATE OR REPLACE TABLE enriched AS SELECT * FROM enriched_df")
    conn.close()

    logger.success(f"Enriched {len(enriched_df):,} companies → {DB_PATH}")


if __name__ == "__main__":
    main()
