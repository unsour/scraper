# Scrapling — Docker Setup

Web scraping с обходом антибот-защиты. Всё работает в Docker, сервер не трогаем.

## Быстрый старт на сервере

```bash
# Первый запуск — скачать образ и поднять контейнер
docker compose up -d

# Войти в контейнер
docker compose exec scrapling bash
```

## Запуск скриптов

Все скрипты лежат в папке `scripts/`, результаты пишутся в `output/`.

```bash
# Простой HTTP-запрос (без браузера, быстро)
docker compose exec scrapling python scripts/example_simple.py

# Стелс-режим (Chrome + обход bot detection)
docker compose exec scrapling python scripts/example_stealth.py

# Паук — обход нескольких страниц
docker compose exec scrapling python scripts/example_spider.py
# → результат в output/quotes.json
```

## Написать свой скрапер

Создай файл в `scripts/my_scraper.py`:

```python
from scrapling.fetchers import Fetcher

page = Fetcher.get("https://example.com/")

# CSS-селекторы
title = page.css("h1::text").get()          # первый элемент
links = page.css("a::attr(href)").getall()  # все элементы

print(title)
```

Запусти:
```bash
docker compose exec scrapling python scripts/my_scraper.py
```

## Три режима фетчера

| Режим | Класс | Когда использовать |
|-------|-------|--------------------|
| HTTP-запрос | `Fetcher` | Обычные сайты без JS |
| Стелс-браузер | `StealthyFetcher` | Cloudflare, антибот |
| Полный браузер | `PlayWrightFetcher` | SPA, сложный JS |

```python
from scrapling.fetchers import Fetcher, StealthyFetcher, PlayWrightFetcher

# HTTP (без браузера)
page = Fetcher.get("https://example.com/")

# Стелс Chrome (headless)
page = StealthyFetcher.fetch("https://example.com/", headless=True)

# Playwright (полный браузер)
page = PlayWrightFetcher.fetch("https://example.com/", headless=True)
```

## CSS-селекторы

```python
# Получить текст
page.css("h1::text").get()

# Получить атрибут
page.css("a::attr(href)").get()

# Все элементы списком
page.css(".item::text").getall()

# Вложенный поиск
for card in page.css(".card"):
    title = card.css("h2::text").get()
    price = card.css(".price::text").get()
```

## Управление контейнером

```bash
# Статус
docker compose ps

# Логи
docker compose logs -f

# Остановить
docker compose stop

# Пересоздать (после обновления образа)
docker compose pull && docker compose up -d
```

## Структура папок

```
scraper/
├── docker-compose.yml   # конфиг Docker
├── scripts/             # твои скрипты (монтируется в контейнер)
│   ├── example_simple.py
│   ├── example_stealth.py
│   └── example_spider.py
└── output/              # результаты скрапинга
```
