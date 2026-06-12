import pandas as pd


def merge_companies_with_jobs(
    companies: pd.DataFrame,
    jobs: pd.DataFrame,
) -> pd.DataFrame:
    unique_companies = companies.drop_duplicates(subset=["company_name_normalized"])

    merged = jobs.merge(
        unique_companies,
        on="company_name_normalized",
        how="left",
        suffixes=("_job", "_ch"),
    )

    # Prefer official CH name; fall back to what LinkedIn/Indeed reported
    if "company_name" in merged.columns:
        merged["company_name"] = merged["company_name"].fillna(
            merged.get("company_name_raw", "")
        )
    else:
        merged["company_name"] = merged.get("company_name_raw", "")

    return merged


def select_output_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for col in columns:
        if col not in df.columns:
            df = df.assign(**{col: None})

    return df[columns].copy()
