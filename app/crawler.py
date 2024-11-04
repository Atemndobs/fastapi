from fastapi import APIRouter, HTTPException
import requests
from .models import CrawlRequest, CrawlResponse, ApartmentDetails
from .utils import crawl_apartment_data

router = APIRouter()

@router.post("/crawl", response_model=CrawlResponse)
async def crawl_apartment(crawl_request: CrawlRequest):
    return crawl_apartment_data(crawl_request)