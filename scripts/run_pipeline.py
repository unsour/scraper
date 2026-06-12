from pipeline.companies import load_companies
from pipeline.exporter import export
from pipeline.jobs import scrape_all_jobs
from pipeline.merger import merge_companies_with_jobs, select_output_columns
from pipeline.scoring import add_hiring_velocity, add_quality_score
from pipeline.tech_stack import add_tech_stack
from pipeline.constants import OUTPUT_COLUMNS


def run() -> None:
    print("\n=== [1/6] Loading Companies House data ===")
    companies = load_companies()

    print("\n=== [2/6] Scraping job listings (LinkedIn + Indeed) ===")
    jobs = scrape_all_jobs()

    print("\n=== [3/6] Extracting tech stack from descriptions ===")
    jobs = add_tech_stack(jobs)

    print("\n=== [4/6] Merging companies + jobs ===")
    merged = merge_companies_with_jobs(companies, jobs)
    print(f"  Matched {merged['company_number'].notna().sum():,} / {len(merged):,} jobs to CH records")

    print("\n=== [5/6] Calculating hiring_velocity + quality_score ===")
    merged = add_hiring_velocity(merged)
    merged = add_quality_score(merged)

    print("\n=== [6/6] Exporting results ===")
    final = select_output_columns(merged, OUTPUT_COLUMNS)
    csv_path, parquet_path = export(final)

    print(f"\n✓ Done — {len(final):,} leads")
    print(f"  CSV:     {csv_path}")
    print(f"  Parquet: {parquet_path}")


if __name__ == "__main__":
    run()
