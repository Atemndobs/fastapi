from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from .models import DistanceRequest, DistanceResponse, CrawlRequest
from .utils import get_distance_data, get_homegate_address

router = APIRouter()

# Update the API endpoint for distance calculation
@router.post("/get_distance", response_model=DistanceResponse)
async def get_distance(distance_request: DistanceRequest):
    try:
        # Check if platform is Homegate and retrieve address if needed
        if distance_request.platform == "homegate.ch" and distance_request.urls:
            # Create a CrawlRequest instance with the relevant data
            crawl_request = CrawlRequest(
                address=distance_request.address,
                platform=distance_request.platform,
                appart_url=distance_request.urls[0],
                id=distance_request.id,
                target_address=distance_request.target_address,
                urls=distance_request.urls
            )
            # Get the resolved address using the crawl request
            resolved_address = get_homegate_address(crawl_request)
            print("Resolved address: {}".format(resolved_address))
            if not resolved_address:
                raise HTTPException(status_code=404, detail="Address not found for Homegate listing")

            # Update the address in the distance_request object
            distance_request.address = resolved_address

        # Proceed with distance calculation
        return get_distance_data(distance_request)
    
    except HTTPException as e:
        raise e  # Pass through HTTP exceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")