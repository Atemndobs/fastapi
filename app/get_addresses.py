from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from .models import CrawlRequest
from .utils import get_addresses

router = APIRouter()

# Updated CrawlRequest model to accept the required fields
class CrawlRequest(BaseModel):
    address: Optional[str] = None
    platform: Optional[str] = "flatfox.ch"  # Default platform
    id: Optional[str] = "default_id"  # Default id
    target_address: Optional[str] = "default_target"  # Default target address
    urls: List[str]  # List of URLs

# Response model to return a list of addresses
class AddressesResponse(BaseModel):
    addresses: List[str]  # List of addresses found

# Update the API endpoint for address fetching
@router.post("/get_addresses", response_model=AddressesResponse)
async def get_addresses_from_url(distance_request: CrawlRequest):
    try:
        # Extract the URL from the request body and put it into the urls list
        urls = distance_request.urls

        # Ensure the URLs list is not empty
        if not urls:
            raise HTTPException(status_code=400, detail="At least one URL must be provided")

        # Create a CrawlRequest instance using the provided data
        crawl_request = CrawlRequest(
            address=distance_request.address,
            platform=distance_request.platform,
            appart_url=urls[0],  # Use the first URL
            id=distance_request.id,
            target_address=distance_request.target_address,
            urls=urls  # URLs list
        )

        # Retrieve the list of addresses from the crawling service
        addresses = get_addresses(crawl_request)

        print(f"Resolved addresses: {addresses}")
        
        # If no addresses are found, raise a 404 error
        if not addresses:
            raise HTTPException(status_code=404, detail="No addresses found for the provided listing")

        # Return the list of addresses
        return {"addresses": addresses}

    except HTTPException as e:
        raise e  # Re-raise HTTP exceptions to be handled by FastAPI
    except Exception as e:
        # Catch any other exceptions and return a generic error response
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
