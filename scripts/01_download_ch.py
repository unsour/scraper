import io
import os
import zipfile
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
from loguru import logger
from scrapling.fetchers import Fetcher

load_dotenv()

INDEX_URL = "https://download.companieshouse.gov.uk/en_output.html"
ZIP_MARKER = "BasicCompanyDataAsOneFile"
MIN_DATE = "2015-01-01"
MAX_COMPANIES = int(os.getenv("MAX_COMPANIES", "50000"))

CH_COLUMNS = {
    "CompanyName": "company_name",
    "CompanyNumber": "company_number",
    "SICCode.SicText_1": "sic_description",
    "RegAddress.PostTown": "city",
    "IncorporationDate": "incorporation_date",
    "CompanyStatus": "_status",
}

RAW_DIR = Path("/app/output/raw")
CACHE_DIR = Path("/app/output/cache")
OUT_PATH = RAW_DIR / "ch_basic.csv"


def _find_zip_url() -> str:
    page = Fetcher.get(INDEX_URL)
    links = page.css("a::attr(href)").getall()
    zip_links = [l for l in links if ZIP_MARKER in l and l.endswith(".zip")]

    if not zip_links:
        raise RuntimeError("Companies House ZIP link not found")

    link = zip_links[0]
    if link.startswith("http"):
        return link
    return f"https://download.companieshouse.gov.uk/{link}"


def _download(url: str) -> Path:
    dest = CACHE_DIR / url.split("/")[-1]
    if dest.exists():
        logger.info(f"Using cached: {dest.name}")
        return dest

    logger.info(f"Downloading {dest.name} (~600MB)...")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, stream=True, timeout=600)
    resp.raise_for_status()

    with open(dest, "wb") as f:
        for chunk in resp.iter_content(4 * 1024 * 1024):
            f.write(chunk)
    return dest


def _open_csv(zip_path: Path) -> io.BytesIO:
    with zipfile.ZipFile(zip_path) as zf:
        csvs = [n for n in zf.namelist() if n.endswith(".csv")]
        if not csvs:
            raise RuntimeError("No CSV inside ZIP")
        return io.BytesIO(zf.read(csvs[0]))


def _parse_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    available = {k: v for k, v in CH_COLUMNS.items() if k in chunk.columns}
    df = chunk[list(available)].rename(columns=available)

    is_active = df["_status"] == "Active"
    df = df[is_active].drop(columns=["_status"])

    df["incorporation_date"] = pd.to_datetime(
        df["incorporation_date"], dayfirst=True, errors="coerce"
    )
    is_recent = df["incorporation_date"] >= MIN_DATE
    return df[is_recent]


def main() -> None:
    logger.info("=== 01_download_ch.py ===")
    url = _find_zip_url()
    zip_path = _download(url)

    logger.info("Parsing CSV chunks...")
    csv_buf = _open_csv(zip_path)

    frames: list[pd.DataFrame] = []
    total = 0

    for chunk in pd.read_csv(csv_buf, chunksize=100_000, low_memory=False):
        parsed = _parse_chunk(chunk)
        frames.append(parsed)
        total += len(parsed)
        if total >= MAX_COMPANIES:
            break

    df = pd.concat(frames, ignore_index=True).head(MAX_COMPANIES)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)

    logger.success(f"Saved {len(df):,} companies → {OUT_PATH}")


if __name__ == "__main__":
    main()
