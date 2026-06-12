import subprocess
import sys
from pathlib import Path

from loguru import logger

STEPS: list[str] = [
    "scripts/01_download_ch.py",
    "scripts/02_scrape_jobs.py",
    "scripts/03_merge.py",
    "scripts/04_enrich.py",
    "scripts/05_export.py",
]


def _run_step(script: str) -> None:
    script_path = Path(script)
    logger.info(f"▶ {script_path.name}")

    result = subprocess.run(
        [sys.executable, script],
        capture_output=False,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Step failed with exit code {result.returncode}: {script}")

    logger.success(f"✓ {script_path.name}")


def main() -> None:
    logger.info("=== Pipeline start ===")

    for step in STEPS:
        _run_step(step)

    logger.success("=== Pipeline complete ===")


if __name__ == "__main__":
    main()
