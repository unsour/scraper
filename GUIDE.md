# Полный мануал: парсинг данных с сайта через Scrapling

## Содержание
1. [Подключение к серверу](#1-подключение-к-серверу)
2. [Шаг 1 — Изучить сайт](#2-шаг-1--изучить-сайт)
3. [Шаг 2 — Выбрать режим фетчера](#3-шаг-2--выбрать-режим-фетчера)
4. [Шаг 3 — Написать скрипт](#4-шаг-3--написать-скрипт)
5. [Шаг 4 — Запустить и проверить](#5-шаг-4--запустить-и-проверить)
6. [Шаг 5 — Сохранить результат](#6-шаг-5--сохранить-результат)
7. [Шаг 6 — Обход блокировок](#7-шаг-6--обход-блокировок)
8. [Шаг 7 — Парсинг нескольких страниц](#8-шаг-7--парсинг-нескольких-страниц)
9. [CSS-селекторы — шпаргалка](#9-css-селекторы--шпаргалка)
10. [Типичные ошибки и решения](#10-типичные-ошибки-и-решения)

---

## 1. Подключение к серверу

```bash
ssh root@13.140.170.244
cd /opt/scraper
```

---

## 2. Шаг 1 — Изучить сайт

Прежде чем писать код, нужно понять структуру сайта.

### Открой DevTools в браузере
1. Перейди на нужный сайт
2. Нажми `F12` (или `Cmd+Opt+I` на Mac)
3. Перейди на вкладку **Elements**

### Найди нужный элемент
1. Нажми на иконку курсора (инспектор) в левом верхнем углу DevTools
2. Кликни на элемент на странице, который хочешь спарсить
3. В панели Elements подсветится HTML-код этого элемента

### Определи CSS-селектор
Смотри на атрибуты тега:
```html
<!-- Пример: карточка товара -->
<div class="product-card" data-id="123">
  <h2 class="product-title">Название товара</h2>
  <span class="price">1 500 ₽</span>
  <a href="/product/123" class="product-link">Подробнее</a>
</div>
```

Из этого HTML строишь селекторы:
- `.product-card` — карточка товара
- `.product-title` — заголовок
- `.price` — цена
- `.product-link` — ссылка

### Быстрый способ: скопировать селектор
В DevTools → правая кнопка на элементе → **Copy** → **Copy selector**
Но учти: автоматически скопированный селектор обычно слишком длинный и хрупкий.
Лучше упростить его вручную.

---

## 3. Шаг 2 — Выбрать режим фетчера

| Признак | Фетчер |
|---------|--------|
| Сайт отдаёт HTML сразу (без JS) | `Fetcher` |
| Сайт требует JS для отображения данных | `StealthyFetcher` |
| Нужно кликать, заполнять формы, скроллить | `PlayWrightFetcher` |
| Есть Cloudflare / антибот / капча | `StealthyFetcher` |

### Как проверить, нужен ли JS
Открой терминал и выполни:
```bash
curl -s "https://example.com/catalog" | grep "название_товара"
```
- Если нашло — сайт отдаёт данные без JS. Используй `Fetcher`.
- Если пусто — данные грузятся через JS. Используй `StealthyFetcher`.

---

## 4. Шаг 3 — Написать скрипт

Создай файл скрипта локально в папке `scripts/`:

### Вариант A: простой сайт (без JS)

```python
# scripts/parse_catalog.py
import json
from scrapling.fetchers import Fetcher

TARGET_URL = "https://example.com/catalog"

page = Fetcher.get(TARGET_URL)

items = []
for card in page.css(".product-card"):
    title = card.css(".product-title::text").get()
    price = card.css(".price::text").get()
    link = card.css(".product-link::attr(href)").get()

    items.append({
        "title": title,
        "price": price,
        "link": link,
    })

with open("/app/output/catalog.json", "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)

print(f"Спарсено: {len(items)} товаров")
```

### Вариант B: сайт с JS / антиботом

```python
# scripts/parse_catalog_stealth.py
import json
from scrapling.fetchers import StealthyFetcher

TARGET_URL = "https://example.com/catalog"

page = StealthyFetcher.fetch(
    TARGET_URL,
    headless=True,      # без открытия окна браузера
    network_idle=True,  # ждать пока загрузятся все запросы
)

items = []
for card in page.css(".product-card"):
    title = card.css(".product-title::text").get()
    price = card.css(".price::text").get()

    items.append({"title": title, "price": price})

with open("/app/output/catalog.json", "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)

print(f"Спарсено: {len(items)} товаров")
```

### Вариант C: нужно кликать / скроллить

```python
# scripts/parse_with_actions.py
import json
from scrapling.fetchers import PlayWrightFetcher

TARGET_URL = "https://example.com/catalog"

page = PlayWrightFetcher.fetch(
    TARGET_URL,
    headless=True,
    wait_selector=".product-card",  # ждать появления элемента
)

# Прокрутить страницу вниз (для lazy-load)
page.scroll_to_bottom()

items = []
for card in page.css(".product-card"):
    title = card.css(".product-title::text").get()
    price = card.css(".price::text").get()
    items.append({"title": title, "price": price})

with open("/app/output/catalog.json", "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)

print(f"Спарсено: {len(items)} товаров")
```

---

## 5. Шаг 4 — Запустить и проверить

### Загрузить скрипт на сервер (с локального Mac)
```bash
# Из локальной папки /Users/dmitriiusenko/vibecode/scraper
scp scripts/parse_catalog.py root@13.140.170.244:/opt/scraper/scripts/
```

Или запушить в git и подтянуть на сервере:
```bash
# Локально
git add scripts/parse_catalog.py
git commit -m "add catalog parser"
git push

# На сервере
ssh root@13.140.170.244
cd /opt/scraper && git pull
```

### Запустить
```bash
# На сервере
cd /opt/scraper
docker compose exec scrapling python scripts/parse_catalog.py
```

### Проверить результат
```bash
# Посмотреть содержимое файла
docker compose exec scrapling cat /app/output/catalog.json

# Или скачать на локальный Mac
scp root@13.140.170.244:/opt/scraper/output/catalog.json ~/Desktop/
```

---

## 6. Шаг 5 — Сохранить результат

### JSON (рекомендуется)
```python
import json

with open("/app/output/result.json", "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)
```

### CSV (для Excel)
```python
import csv

with open("/app/output/result.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["title", "price", "link"])
    writer.writeheader()
    writer.writerows(items)
```

### Вывод в терминал (для отладки)
```python
for item in items[:5]:  # первые 5
    print(item)
```

---

## 7. Шаг 6 — Обход блокировок

### Добавить задержку между запросами
```python
import time
import random
from scrapling.fetchers import Fetcher

urls = ["https://example.com/page/1", "https://example.com/page/2"]

for url in urls:
    page = Fetcher.get(url)
    # ... парсинг ...

    delay = random.uniform(1.5, 4.0)  # случайная задержка 1.5–4 сек
    time.sleep(delay)
```

### Добавить заголовки браузера
```python
from scrapling.fetchers import Fetcher

page = Fetcher.get(
    "https://example.com/",
    headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9",
    }
)
```

### Сайт с Cloudflare
```python
from scrapling.fetchers import StealthyFetcher

page = StealthyFetcher.fetch(
    "https://protected-site.com/",
    headless=True,
    network_idle=True,
    # Scrapling автоматически подбирает fingerprint браузера
)
```

---

## 8. Шаг 7 — Парсинг нескольких страниц

### Постраничная пагинация (?page=1, ?page=2, ...)
```python
import json
from scrapling.fetchers import Fetcher

BASE_URL = "https://example.com/catalog?page={page}"
MAX_PAGES = 10

all_items = []

for page_num in range(1, MAX_PAGES + 1):
    url = BASE_URL.format(page=page_num)
    page = Fetcher.get(url)

    cards = page.css(".product-card")
    if not cards:
        print(f"Страница {page_num}: пусто, стоп")
        break

    for card in cards:
        all_items.append({
            "title": card.css(".product-title::text").get(),
            "price": card.css(".price::text").get(),
        })

    print(f"Страница {page_num}: +{len(cards)} товаров")

with open("/app/output/all_products.json", "w", encoding="utf-8") as f:
    json.dump(all_items, f, ensure_ascii=False, indent=2)

print(f"Итого: {len(all_items)} товаров")
```

### Кнопка «Следующая страница»
```python
import json
from scrapling.fetchers import Fetcher

START_URL = "https://example.com/catalog"

all_items = []
url = START_URL

while url:
    page = Fetcher.get(url)

    for card in page.css(".product-card"):
        all_items.append({
            "title": card.css(".product-title::text").get(),
            "price": card.css(".price::text").get(),
        })

    next_link = page.css(".pagination .next::attr(href)").get()
    url = next_link  # None если кнопки «далее» нет — цикл завершится
    print(f"Следующая страница: {url}")

with open("/app/output/all_products.json", "w", encoding="utf-8") as f:
    json.dump(all_items, f, ensure_ascii=False, indent=2)
```

---

## 9. CSS-селекторы — шпаргалка

```python
# Текст элемента
page.css("h1::text").get()

# Атрибут элемента
page.css("a::attr(href)").get()
page.css("img::attr(src)").get()

# Первый найденный элемент (или None)
page.css(".price::text").get()

# Все найденные элементы (список)
page.css(".tag::text").getall()

# Поиск внутри элемента
for card in page.css(".product-card"):
    title = card.css("h2::text").get()  # ищет h2 внутри card

# По id
page.css("#main-title::text").get()

# По нескольким классам
page.css(".product.featured::text").get()

# По атрибуту
page.css('input[name="email"]')
page.css('a[href*="/product/"]')  # href содержит /product/

# Дочерний элемент
page.css(".card > h2::text").get()

# Любой вложенный элемент
page.css(".card h2::text").get()
```

---

## 10. Типичные ошибки и решения

### `.get()` возвращает `None`
Селектор не нашёл элемент. Проверь:
1. Правильный ли селектор (скопируй из DevTools)
2. Не загружается ли контент через JS → переключись на `StealthyFetcher`
3. Нет ли опечатки в имени класса

```python
# Защита от None
title = card.css(".title::text").get() or "Без названия"
```

### Пустой список — сайт грузит данные через XHR/fetch
Открой DevTools → **Network** → фильтр **XHR/Fetch**.
Перезагрузи страницу и найди запрос который возвращает нужные данные (обычно JSON).
Тогда можно обращаться напрямую к API:

```python
import json
from scrapling.fetchers import Fetcher

# Прямой запрос к API сайта
response = Fetcher.get("https://example.com/api/products?page=1")
data = json.loads(response.html)
products = data["items"]
```

### Сайт возвращает 403 / блокирует
```python
# Использовать StealthyFetcher вместо Fetcher
from scrapling.fetchers import StealthyFetcher

page = StealthyFetcher.fetch("https://example.com/", headless=True)
```

### Текст с лишними пробелами/переносами
```python
title = card.css(".title::text").get()
title = title.strip() if title else None
```

### Кодировка — кракозябры в JSON
```python
# ensure_ascii=False обязателен для кириллицы
json.dump(items, f, ensure_ascii=False, indent=2)
```
