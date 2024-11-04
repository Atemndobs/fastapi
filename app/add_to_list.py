import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Define the request body schema
class AddToListRequest(BaseModel):
    address: str
    platform: str
    appart_url: str
    id: str
    target_address: str
    urls: list[str]
    include_raw_html: bool = False
    bypass_cache: bool = False
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

router = APIRouter()

@router.post("/add_to_list")
async def add_to_list(request: AddToListRequest):
    distance_url = "https://fastapi.curator.atemkeng.eu/api/v1/apartment/get_distance"
    crawl_url = "https://fastapi.curator.atemkeng.eu/api/v1/apartment/crawl"
    n8n_webhook_url = "https://n8n.atemkeng.de/webhook/5fb74a0f-a6a9-402d-aa5f-6271e874a769"

    # Step 1: Request distance data
    distance_payload = {
        "address": request.address,
        "platform": request.platform,
        "appart_url": request.appart_url,
        "id": request.id,
        "target_address": request.target_address,
        "urls": request.urls
    }
    distance_response = requests.post(distance_url, json=distance_payload)

    if not distance_response.ok:
        raise HTTPException(status_code=distance_response.status_code, detail="Failed to fetch distance data")

    distance_data = distance_response.json()

    # Step 2: Request apartment details from crawl endpoint
    crawl_payload = {
        "address": request.address,
        "platform": request.platform,
        "appart_url": request.appart_url,
        "id": request.id,
        "target_address": request.target_address,
        "urls": request.urls,
        "include_raw_html": request.include_raw_html,
        "bypass_cache": request.bypass_cache,
        "extract_blocks": request.extract_blocks,
        "word_count_threshold": request.word_count_threshold,
        "extraction_strategy": request.extraction_strategy,
        "extraction_strategy_args": request.extraction_strategy_args,
        "chunking_strategy": request.chunking_strategy,
        "chunking_strategy_args": request.chunking_strategy_args,
        "css_selector": request.css_selector,
        "screenshot": request.screenshot,
        "user_agent": request.user_agent,
        "verbose": request.verbose
    }
    crawl_response = requests.post(crawl_url, json=crawl_payload)

    if not crawl_response.ok:
        raise HTTPException(status_code=crawl_response.status_code, detail="Failed to fetch crawl data")

    crawl_data = crawl_response.json()

    # Step 3: Combine results and send to n8n webhook
    combined_data = {
        "distance_data": distance_data,
        "apartment_data": crawl_data
    }

    webhook_response = requests.post(n8n_webhook_url, json=combined_data)

    if not webhook_response.ok:
        raise HTTPException(status_code=webhook_response.status_code, detail="Failed to send data to webhook")

    return {"status": "success", "message": "Data sent to n8n webhook", "data": combined_data}
