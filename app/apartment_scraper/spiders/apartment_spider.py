# app/apartment_scraper/spiders/apartment_spider.py


import scrapy
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
import crochet  # Crochet allows integrating Twisted with asyncio/FastAPI

class ApartmentSpider(scrapy.Spider):
    name = "apartment"

    def __init__(self, url, **kwargs):
        self.start_urls = [url]
        super().__init__(**kwargs)

    def parse(self, response):
        yield {
            "title": response.css("h1::text").get(),
            "address": response.css(".street-address::text").get(),
            "gross_rent": response.xpath("//dt[contains(text(), 'Gross rent')]/following-sibling::dd[1]/text()").get(),
            "net_rent": response.xpath("//dt[contains(text(), 'Net rent')]/following-sibling::dd[1]/text()").get(),
            "utilities": response.xpath("//dt[contains(text(), 'Utilities')]/following-sibling::dd[1]/text()").get(),
            "reference": response.xpath("//dt[contains(text(), 'Reference')]/following-sibling::dd[1]/text()").get(),
            "number_of_rooms": response.xpath("//dt[contains(text(), 'Number of rooms')]/following-sibling::dd[1]/text()").get(),
            "floor": response.xpath("//dt[contains(text(), 'Floor')]/following-sibling::dd[1]/text()").get(),
            "living_space": response.xpath("//dt[contains(text(), 'Living space')]/following-sibling::dd[1]/text()").get(),
            "year_of_construction": response.xpath("//dt[contains(text(), 'Year of construction')]/following-sibling::dd[1]/text()").get(),
            "facilities": response.xpath("//dt[contains(text(), 'Facilities')]/following-sibling::dd[1]/text()").get(),
            "availability": response.xpath("//dt[contains(text(), 'Available')]/following-sibling::dd[1]/text()").get(),
            "description": response.css(".description::text").getall(),  # Gets all lines of description
        }

crochet.setup()  # Initialize Crochet

@crochet.run_in_reactor
def run_spider(url):
    settings = get_project_settings()
    runner = CrawlerRunner(settings)
    deferred = runner.crawl(ApartmentSpider, url=url)  # Pass URL as argument
    deferred.addCallback(lambda _: None)  # Ensure the deferred completes
    return deferred
