from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import requests


router = APIRouter()

# Define the request model with optional fields and default values
class CrawlRequest(BaseModel):
    address: str
    platform: str
    appart_url: str
    id: str
    target_address: str
    urls: List[str] = []  # Add this to the model
    extract_blocks: bool = True
    word_count_threshold: int = 5
    extraction_strategy: str = "NoExtractionStrategy"
    extraction_strategy_args: dict = {}
    chunking_strategy: str = "RegexChunking"
    chunking_strategy_args: dict = {}
    css_selector: str = ""
    screenshot: bool = False
    user_agent: str = ""
    verbose: bool = True

# Endpoint for forwarding the request payload with optional parameters
@router.post("/crawler_bak")
async def crawl_apartment(crawl_request: CrawlRequest):
    try:
        # Send the request to Crawl4AI with the JSON payload
        response = requests.post(
            "https://scrape.cloud.atemkeng.de/crawl",
            headers={"Content-Type": "application/json"},
            json=crawl_request.dict(exclude_none=True)  # Exclude fields that are None
        )
        response.raise_for_status()  # Raise error for HTTP issues

        # Return the response JSON from Crawl4AI
        return response.json()

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Request to Crawl4AI failed: {str(e)}")

