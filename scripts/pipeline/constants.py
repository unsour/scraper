from pathlib import Path

COMPANIES_HOUSE_INDEX_URL = "https://download.companieshouse.gov.uk/en_output.html"
COMPANIES_HOUSE_ZIP_PATTERN = "BasicCompanyDataAsOneFile"

CH_COLUMN_MAP: dict[str, str] = {
    "CompanyName": "company_name",
    "CompanyNumber": "company_number",
    "SICCode.SicText_1": "sic_description",
    "RegAddress.PostTown": "city",
    "IncorporationDate": "incorporation_date",
    "CompanyStatus": "_status",
}

CH_ACTIVE_STATUS = "Active"
CH_CHUNK_SIZE = 100_000

TECH_KEYWORDS: list[str] = [
    "Python", "JavaScript", "TypeScript", "React", "Vue", "Angular",
    "Node.js", "Django", "FastAPI", "Flask", "Spring", "Rails",
    "AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
    "GraphQL", "REST", "Go", "Rust", "Java", "Kotlin", "Swift",
    "CI/CD", "Linux", "Spark", "Kafka", "Airflow",
    "Machine Learning", "LLM", "TensorFlow", "PyTorch", "Pandas",
]

JOBS_SEARCH_TERMS: list[str] = [
    "software engineer",
    "data engineer",
    "backend developer",
    "frontend developer",
    "devops engineer",
    "fullstack developer",
]

JOBS_RESULTS_PER_TERM = 100
JOBS_HOURS_OLD = 168  # 1 week

OUTPUT_COLUMNS: list[str] = [
    "company_name",
    "company_number",
    "sic_description",
    "city",
    "incorporation_date",
    "job_title",
    "salary_min",
    "salary_max",
    "is_remote",
    "tech_stack",
    "hiring_velocity",
    "quality_score",
]

QUALITY_MAX = 100
SALARY_SCORE = 25
REMOTE_SCORE = 15
TECH_SCORE_PER_SKILL = 5
TECH_SCORE_MAX = 30
COMPANY_NUMBER_SCORE = 15
CITY_SCORE = 10
SIC_SCORE = 5

OUTPUT_DIR = Path("/app/output/final")
CACHE_DIR = Path("/app/output/cache")
