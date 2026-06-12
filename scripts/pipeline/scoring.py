import pandas as pd

from pipeline.constants import (
    CITY_SCORE,
    COMPANY_NUMBER_SCORE,
    QUALITY_MAX,
    REMOTE_SCORE,
    SALARY_SCORE,
    SIC_SCORE,
    TECH_SCORE_MAX,
    TECH_SCORE_PER_SKILL,
)


def _salary_score(row: pd.Series) -> int:
    has_min = pd.notna(row.get("salary_min"))
    has_max = pd.notna(row.get("salary_max"))
    return SALARY_SCORE if (has_min or has_max) else 0


def _remote_score(row: pd.Series) -> int:
    return REMOTE_SCORE if row.get("is_remote") else 0


def _tech_score(row: pd.Series) -> int:
    tech_stack = row.get("tech_stack", "")
    if not tech_stack:
        return 0
    skill_count = len(str(tech_stack).split(", "))
    return min(TECH_SCORE_MAX, skill_count * TECH_SCORE_PER_SKILL)


def _completeness_score(row: pd.Series) -> int:
    score = 0
    if pd.notna(row.get("company_number")):
        score += COMPANY_NUMBER_SCORE
    if pd.notna(row.get("city")) and row.get("city"):
        score += CITY_SCORE
    if pd.notna(row.get("sic_description")) and row.get("sic_description"):
        score += SIC_SCORE
    return score


def _row_score(row: pd.Series) -> int:
    total = (
        _salary_score(row)
        + _remote_score(row)
        + _tech_score(row)
        + _completeness_score(row)
    )
    return min(QUALITY_MAX, total)


def add_hiring_velocity(df: pd.DataFrame) -> pd.DataFrame:
    velocity = df.groupby("company_name_normalized")["job_title"].transform("count")
    return df.assign(hiring_velocity=velocity)


def add_quality_score(df: pd.DataFrame) -> pd.DataFrame:
    return df.assign(quality_score=df.apply(_row_score, axis=1))
