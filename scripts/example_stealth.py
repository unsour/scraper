"""
Stealth browser scraper — bypasses basic bot detection.
Uses headless Chrome with fingerprint spoofing.
"""
from scrapling.fetchers import StealthyFetcher

page = StealthyFetcher.fetch(
    "https://quotes.toscrape.com/",
    headless=True,
    network_idle=True,
)

quotes = page.css(".quote")

for quote in quotes:
    text = quote.css(".text::text").get()
    author = quote.css(".author::text").get()
    print(f"{author}: {text}")
