import io
import zipfile
from pathlib import Path

import pandas as pd
import requests
from scrapling.fetchers import Fetcher

from pipeline.constants import (
    CACHE_DIR,
    CH_ACTIVE_STATUS,
    CH_CHUNK_SIZE,
    CH_COLUMN_MAP,
    COMPANIES_HOUSE_INDEX_URL,
    COMPANIES_HOUSE_ZIP_PATTERN,
)


def _fetch_download_url() -> str:
    page = Fetcher.get(COMPANIES_HOUSE_INDEX_URL)
    links = page.css("a::attr(href)").getall()

    zip_links = [
        link for link in links
        if COMPANIES_HOUSE_ZIP_PATTERN in link and link.endswith(".zip")
    ]

    if not zip_links:
        raise RuntimeError("Companies House download link not found on index page")

    link = zip_links[0]
    if link.startswith("http"):
        return link
    return f"https://download.companieshouse.gov.uk/{link}"


def _download_zip(url: str) -> Path:
    filename = url.split("/")[-1]
    cache_path = CACHE_DIR / filename

    if cache_path.exists():
        print(f"  Using cached file: {cache_path.name}")
        return cache_path

    print(f"  Downloading {filename} (~600MB, please wait)...")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    response = requests.get(url, stream=True, timeout=600)
    response.raise_for_status()

    with open(cache_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=4 * 1024 * 1024):
            f.write(chunk)

    return cache_path


def _open_csv_from_zip(zip_path: Path) -> io.BytesIO:
    with zipfile.ZipFile(zip_path) as zf:
        csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
        if not csv_names:
            raise RuntimeError(f"No CSV found inside {zip_path.name}")
        return io.BytesIO(zf.read(csv_names[0]))


def _parse_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    available = {k: v for k, v in CH_COLUMN_MAP.items() if k in chunk.columns}
    result = chunk[list(available.keys())].rename(columns=available)

    is_active = result["_status"] == CH_ACTIVE_STATUS
    result = result[is_active].drop(columns=["_status"])

    result["company_name_normalized"] = (
        result["company_name"].str.upper().str.strip()
    )
    return result


def load_companies() -> pd.DataFrame:
    print("Fetching Companies House download URL...")
    url = _fetch_download_url()

    zip_path = _download_zip(url)

    print("  Parsing CSV in chunks...")
    csv_buffer = _open_csv_from_zip(zip_path)

    chunks: list[pd.DataFrame] = []
    for chunk in pd.read_csv(csv_buffer, chunksize=CH_CHUNK_SIZE, low_memory=False):
        chunks.append(_parse_chunk(chunk))

    df = pd.concat(chunks, ignore_index=True)
    print(f"  Loaded {len(df):,} active companies")
    return df
