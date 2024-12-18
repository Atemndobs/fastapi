# add_to_list.py

from fastapi import APIRouter, HTTPException
from .models import AddToListRequest
from .utils import get_distance_data, crawl_apartment_data, get_homegate_address
import requests

router = APIRouter()
@router.post("/add_to_list")
async def add_to_list(request: AddToListRequest):
    n8n_webhook_url = "https://n8n.atemkeng.info/webhook/5fb74a0f-a6a9-402d-aa5f-6271e874a769"
    # n8n_webhook_url = "https://n8n.atemkeng.info/webhook-test/5fb74a0f-a6a9-402d-aa5f-6271e874a769"

    # Step 1: Check platform and fetch data accordingly
    if request.platform == "flatfox.ch":
        # For flatfox.ch, proceed as usual
        try:
            distance_data = get_distance_data(request)
        except HTTPException as e:
            raise HTTPException(status_code=e.status_code, detail="Failed to fetch distance data")

        try:
            crawl_data = crawl_apartment_data(request)
        except HTTPException as e:
            raise HTTPException(status_code=e.status_code, detail="Failed to fetch crawl data")

    elif request.platform == "homegate.ch":
        # For homegate.ch, use the apprturl to get the address
        try:
            address = get_homegate_address(request)
        except HTTPException as e:
            raise HTTPException(status_code=e.status_code, detail="Failed to fetch address for homegate.ch")

        # Update request object with the address fetched from apprturl
        request.address = address  # Assuming `address` is a field in AddToListRequest

        # Fetch distance and crawl data using the updated address
        try:
            distance_data = get_distance_data(request)
        except HTTPException as e:
            raise HTTPException(status_code=e.status_code, detail="Failed to fetch distance data")

        try:
            crawl_data = crawl_apartment_data(request)
        except HTTPException as e:
            raise HTTPException(status_code=e.status_code, detail="Failed to fetch crawl data")

    else:
        raise HTTPException(status_code=400, detail="Unsupported platform")

    # Step 2: Combine data and send to n8n webhook
    combined_data = {
        "distance_data": distance_data.dict(),
        "apartment_data": crawl_data.dict()
    }

    webhook_response = requests.post(n8n_webhook_url, json=combined_data)
    if not webhook_response.ok:
        raise HTTPException(status_code=webhook_response.status_code, detail="Failed to send data to webhook")

    return {"status": "success", "message": "Data sent to n8n webhook", "data": combined_data}
