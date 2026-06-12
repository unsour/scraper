# scraper — CLAUDE.md

## Проект
B2B lead pipeline: Companies House bulk CSV + JobSpy → DuckDB merge → LLM enrichment → CSV/Parquet export.

## Сервер
- Host: `13.140.170.244`, SSH root
- Путь: `/opt/scraper`
- Всё через Docker, сервер напрямую не трогать

## Запуск
```bash
docker compose exec scrapling python scripts/run_pipeline.py
```

## Структура скриптов
| Файл | Что делает |
|------|-----------|
| `scripts/01_download_ch.py` | Скачивает Companies House bulk CSV, фильтрует Active + 2015+ |
| `scripts/02_scrape_jobs.py` | JobSpy: LinkedIn + Indeed UK → JSONL |
| `scripts/03_merge.py` | DuckDB: exact + fuzzy join (rapidfuzz >= 0.88) |
| `scripts/04_enrich.py` | LLM обогащение через DeepSeek (Fireworks/OpenRouter) |
| `scripts/05_export.py` | Фильтр quality_score >= 60 → CSV + Parquet |
| `scripts/run_pipeline.py` | Оркестратор, стоп при ошибке любого шага |
| `scripts/pipeline/` | Вспомогательные модули (константы, парсинг) |

## Переменные окружения
Файл `.env` в корне (см. `.env.example`).

## Правила кода (все 103 правила из памяти)
- Макс 150 строк на файл
- Функции <= 30 строк
- Один файл = одна сущность
- Ранние return везде
- Никакого Any, все типы явные
- Все внешние данные через явную валидацию
- Ошибки через loguru, не print
- Комментарии только про "почему"
