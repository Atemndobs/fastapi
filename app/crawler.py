from fastapi import APIRouter, HTTPException
import requests
from .models import CrawlRequest, CrawlResponse, ApartmentDetails, ApartmentSearchResponse, PksRequest
from .utils import crawl_apartment_data, crawl_url, extract_pks_from_html, fetch_apartment_data
from typing import List
import json
from .models import PksRequest, CrawlRequest


router = APIRouter()

@router.post("/crawl", response_model=CrawlResponse)
async def crawl_apartment(crawl_request: CrawlRequest):
    return crawl_apartment_data(crawl_request)

# @router.post("/search_apartments")
# async def search_apartments(crawl_request: CrawlRequest):
#     try:
#         crawl_result = crawl_url(crawl_request)
#         result = extract_apartment_urls(crawl_result)
#         return result
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))



# @router.post("/search_apartments")
# async def search_apartments(crawl_request: CrawlRequest):
#     try:
#         # Get the HTML content from the crawl request
#         result = crawl_url(crawl_request)
        
#         # Assuming the HTML is in a field called 'html_content' in result
#         html_content = result.get("html_content", "")
        
#         # Extract URLs from the HTML content
#         apartment_urls = extract_apartment_urls(html_content)
        
#         return {"apartment_urls": apartment_urls}
    
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


@router.post("/search_apartments")
async def search_apartments(request: CrawlRequest):
    try:
        # Step 1: Fetch raw HTML content
        html_content = crawl_url(request)
        
        # Step 2: Extract pks from HTML
        pks = extract_pks_from_html(html_content)
        
        if not pks:
            raise HTTPException(status_code=404, detail="No PKs found in the HTML content.")
        
        # Step 3: Define the API URL and fetch apartment URLs
        api_url = "https://flatfox.ch/api/v1/public-listing/"
        apartment_urls = fetch_apartment_data(api_url, pks)
        
        return {"apartment_urls": apartment_urls}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))