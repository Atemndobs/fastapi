from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel
from .apartment_scraper.scraper import scrape_apartment
import requests

router = APIRouter()

class Apartment(BaseModel):
    address: str
    platform: str
    appart_url: str
    id: str

class ApartmentDetails(BaseModel):
    title: str
    address: str
    gross_rent: str
    net_rent: str
    utilities: str
    reference: str
    number_of_rooms: str
    floor: str
    living_space: str
    year_of_construction: str
    facilities: str
    availability: str
    description: list
    distance: str = None  # New field for distance
    duration: str = None  # New field for duration

@router.post("/scrape_apartment")
async def scrape_apartment_endpoint(apartments: List[Apartment]):
    results = []
    target_address = "Bahnhofstrasse 94, 5000 Aarau, Switzerland"  # Target address
    api_key = "YOUR_API_KEY"  # Replace with your actual API key

    def get_distance(start_address, target_address, api_key):
        url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        params = {
            "origins": start_address,
            "destinations": target_address,
            "key": api_key
        }

        response = requests.get(url, params=params)
        data = response.json()

        if data["status"] == "OK":
            distance_info = data["rows"][0]["elements"][0]
            if distance_info["status"] == "OK":
                distance = distance_info["distance"]["text"]
                duration = distance_info["duration"]["text"]
                return distance, duration
            else:
                return None, None
        else:
            print(f"Error: {data['error_message']}")
            return None, None

    for apartment in apartments:
        try:
            details = scrape_apartment(apartment.appart_url)  # No await needed
            
            # Get distance and duration
            distance, duration = get_distance(apartment.address, target_address, api_key)
            
            results.append({
                "address": apartment.address,
                "platform": apartment.platform,
                "appart_url": apartment.appart_url,
                "id": apartment.id,
                "details": {**details, "distance": distance, "duration": duration},
            })
        except Exception as e:
            # Log the error message and raise an HTTPException
            print(f"Error scraping apartment {apartment.id}: {e}")
            raise HTTPException(status_code=500, detail=f"Error scraping apartment: {str(e)}")
    return results
