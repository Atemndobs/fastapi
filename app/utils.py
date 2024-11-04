# utils.py

import requests
from fastapi import HTTPException
from .models import DistanceRequest, DistanceResponse, TransitDetails, ModeDistance, TransitInfo, CrawlRequest, CrawlResponse, ApartmentDetails
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import os
# Load environment variables from .env file
load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

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


def get_distance_data(distance_request: DistanceRequest) -> DistanceResponse:
    try:
        origin = distance_request.address
        destination = distance_request.target_address
        # Request distance info for each travel mode
        driving_info = get_distance_info(origin, destination, "driving")
        walking_info = get_distance_info(origin, destination, "walking")
        bicycling_info = get_distance_info(origin, destination, "bicycling")
        transit_info = get_transit_info(origin, destination)

        # Log transit_info for debugging
        print("Transit Info:", transit_info)

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

# Function to extract apartment details from HTML
def extract_apartment_details(html_content: str) -> ApartmentDetails:
    soup = BeautifulSoup(html_content, 'html.parser')

        # Helper function to safely extract text using a CSS selector
    def safe_get_text(selector):
        element = soup.select_one(selector)
        return element.get_text(strip=True) if element else "N/A"

    # Helper function to get values associated with specific labels
    def get_value_for_label(label):
        label_cell = soup.find(text=label)
        if label_cell:
            return label_cell.find_parent('td').find_next_sibling('td').get_text(strip=True)
        return "N/A"

    # Initialize an ApartmentDetails object with default values
    details = ApartmentDetails(
        title=safe_get_text("h1"),
        address=safe_get_text("h2"),
        gross_rent="N/A",
        net_rent="N/A",
        utilities="N/A",
        reference="N/A",
        number_of_rooms="N/A",
        floor="N/A",
        living_space="N/A",
        facilities=[],  # Initialize as an empty list
        availability="N/A",
        year_of_construction="N/A",
        description="N/A",
        table_items=[]
    )

    # Extract table items for debugging and response
    table_items = []

    # Extract details using the updated logic for table items
    for table in soup.find_all('table'):
        for row in table.find_all('tr'):
            cells = row.find_all('td')
            cell_texts = [cell.get_text(strip=True) for cell in cells]
            table_items.append(" | ".join(cell_texts))  # Join cell texts with a pipe
            details.table_items = table_items  # Assign the list of table items to the details

            if len(cells) < 2:  # Ensure there are at least two cells
                continue

            # Get the text from each cell
            label = cells[0].get_text(strip=True)
            value = cells[1].get_text(strip=True)

            # Map the label to the corresponding apartment detail
            if "Gross rent (incl. utilities)" in label:
                details.gross_rent = value
            elif "Net rent (excl. utilities)" in label:
                details.net_rent = value
            elif "Utilities" in label:
                details.utilities = value
            elif "Reference" in label:
                details.reference = value
            elif "Number of rooms" in label:
                details.number_of_rooms = value
            elif "Floor" in label:
                details.floor = value
            elif "Livingspace" in label:
                details.living_space = value
            elif "Facilities" in label:
                # Split the value by commas to form a list if needed
                details.facilities = [facility.strip() for facility in value.split(',')] if value else []
            elif "Available" in label:
                details.availability = value
            elif "Website" in label:
                details.website = value
            elif "Documents" in label:
                details.documents = value
            # Add more mappings as necessary


    # Extract the description if it's in a specific section
    for heading in soup.find_all('h2'):
        if heading.get_text(strip=True) == "Description":
            description_div = heading.find_next('div')
            if description_div:
                paragraphs = description_div.find_all('p')
                details.description = "\n\n".join(p.get_text(strip=True) for p in paragraphs) or "N/A"
            break  # Exit loop once we find and process the description

    return details


def crawl_apartment_data(crawl_request: CrawlRequest) -> CrawlResponse:
    try:
        response = requests.post(
            "https://scrape.cloud.atemkeng.de/crawl",
            headers={"Content-Type": "application/json"},
            json=crawl_request.dict(exclude_none=True)
        )
        response.raise_for_status()
        json_response = response.json()
        
        if json_response.get('results'):
            cleaned_html = json_response['results'][0]['cleaned_html']
        else:
            raise HTTPException(status_code=404, detail="No results found")

        apartment_details = extract_apartment_details(cleaned_html)

        return CrawlResponse(
            address=crawl_request.address,
            platform=crawl_request.platform,
            appart_url=crawl_request.appart_url,
            id=crawl_request.id,
            details=apartment_details
        )

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Request to Crawl4AI failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
