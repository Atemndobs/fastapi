from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import requests
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

router = APIRouter()

# Request model for get_distance
class DistanceRequest(BaseModel):
    address: str
    platform: str
    id: str
    target_address: str
    urls: List[str]

class ModeDistance(BaseModel):
    distance: Optional[float] = None  # Distance in kilometers
    duration: Optional[float] = None  # Duration in minutes

class TransitDetails(BaseModel):
    line_nr: str
    line_name: str
    line_icon: str
    line_color: Optional[str]  # Optional
    vehicle_type: str
    num_stops: str 

class TransitInfo(ModeDistance):
    transit_details: List[TransitDetails]

class DistanceResponse(BaseModel):
    driving: ModeDistance
    walking: ModeDistance
    bicycling: ModeDistance
    transit: TransitInfo

# Function to call Google Maps API for a specific travel mode
def get_distance_info(origin: str, destination: str, mode: str) -> ModeDistance:
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": origin,
        "destinations": destination,
        "mode": mode,
        "key": GOOGLE_MAPS_API_KEY
    }
    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()
    if data['status'] == "OK":
        element = data['rows'][0]['elements'][0]
        if element['status'] == "OK":
            distance = element['distance']['value'] / 1000  # Convert to kilometers
            duration = element['duration']['value'] / 60  # Convert to minutes
            return ModeDistance(distance=distance, duration=duration)
    return ModeDistance(distance=None, duration=None)

def get_transit_info(origin: str, destination: str) -> TransitInfo:
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "mode": "transit",
        # "transit_mode": "bus|subway|train|tram",  # Adjust modes as needed
        "key": GOOGLE_MAPS_API_KEY
    }
    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()
    print(f"API Response for Transit: {data}")  # Debugging line
    if data['status'] == "OK" and data['routes']:
        element = data['routes'][0]['legs'][0]
        distance = element['distance']['value'] / 1000  # Convert to kilometers
        duration = element['duration']['value'] / 60  # Convert to minutes

        # Extract transit details
    transit_details_list = []
    if data.get('routes'):
        for route in data['routes']:
            for leg in route['legs']:
                for step in leg['steps']:
                    if 'transit_details' in step:
                        transit_info = step['transit_details']
                        transit_detail = TransitDetails(
                            line_nr=transit_info['line']['short_name'],  # or transit_info['line']['text']
                            line_name=transit_info['line']['vehicle']['name'],
                            line_icon=transit_info['line']['vehicle']['icon'],
                            line_color=transit_info['line'].get('color'),
                            vehicle_type=transit_info['line']['vehicle']['name'],
                            num_stops=transit_info['num_stops']
                        )
                        transit_details_list.append(transit_detail)
                        print(f"{transit_details_list}")

    return TransitInfo(distance=distance, duration=duration, transit_details=transit_details_list)


@router.post("/get_distance", response_model=DistanceResponse)
async def get_distance(distance_request: DistanceRequest):
    try:
        origin = distance_request.address
        destination = distance_request.target_address

        # Get distances for each travel mode
        driving_info = get_distance_info(origin, destination, "driving")
        walking_info = get_distance_info(origin, destination, "walking")
        bicycling_info = get_distance_info(origin, destination, "bicycling")
        transit_info = get_transit_info(origin, destination)

        # Log transit_info for debugging
        print("Transit Info:", transit_info)  # You can replace this with logging

        # Return the distance response with enhanced transit info
        return DistanceResponse(
            driving=driving_info,
            walking=walking_info,
            bicycling=bicycling_info,
            transit=transit_info,
        )

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Request to Google Maps API failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
