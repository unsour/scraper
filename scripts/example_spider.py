"""
Spider example — crawls multiple pages automatically.
"""
import json
from scrapling.spiders import Spider, Response


class QuotesSpider(Spider):
    name = "quotes"
    start_urls = ["https://quotes.toscrape.com/"]

    async def parse(self, response: Response):
        for quote in response.css(".quote"):
            yield {
                "text": quote.css(".text::text").get(),
                "author": quote.css(".author::text").get(),
                "tags": quote.css(".tag::text").getall(),
            }

        next_page = response.css(".next a::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)


spider = QuotesSpider()
results = spider.start()

with open("/app/output/quotes.json", "w") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"Saved {len(results)} quotes to output/quotes.json")
