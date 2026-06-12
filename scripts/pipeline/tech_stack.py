import re

import pandas as pd

from pipeline.constants import TECH_KEYWORDS

_PATTERNS: dict[str, re.Pattern[str]] = {
    keyword: re.compile(r"\b" + re.escape(keyword) + r"\b", re.IGNORECASE)
    for keyword in TECH_KEYWORDS
}


def _extract_from_text(text: str) -> list[str]:
    if not text:
        return []
    return [kw for kw, pattern in _PATTERNS.items() if pattern.search(text)]


def add_tech_stack(df: pd.DataFrame) -> pd.DataFrame:
    if "description" not in df.columns:
        return df.assign(tech_stack="")

    tech_series = (
        df["description"]
        .fillna("")
        .apply(_extract_from_text)
        .apply(lambda skills: ", ".join(skills))
    )
    return df.assign(tech_stack=tech_series)
