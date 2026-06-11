"""
Simple HTTP scraper example — no browser needed.
Scrapes quotes from quotes.toscrape.com
"""
from scrapling.fetchers import Fetcher

page = Fetcher.get("https://quotes.toscrape.com/")

quotes = page.css(".quote")

for quote in quotes:
    text = quote.css(".text::text").get()
    author = quote.css(".author::text").get()
    print(f"{author}: {text}")
