from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import requests
from bs4 import BeautifulSoup

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
    year_of_construction: Optional[str] = None
    facilities: List[str] = []
    availability: str
    description: str = Field(default="N/A")  # Ensure only one definition here
    distance: Optional[float] = None
    duration: Optional[float] = None
    table_items: List[str] = []
    website: Optional[str] = None
    documents: List[str] = []
    # images: List[str] = []
    # screenshots: List[str] = []


class CrawlResponse(BaseModel):
    address: str
    platform: str
    appart_url: str
    id: str
    details: ApartmentDetails


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


@router.post("/crawl", response_model=CrawlResponse)
async def crawl_apartment(crawl_request: CrawlRequest):
    try:
        # Log the incoming request for debugging
        # print("Received crawl request:", crawl_request)

        # Send the request to Crawl4AI with the JSON payload
        response = requests.post(
            "https://scrape.cloud.atemkeng.de/crawl",
            headers={"Content-Type": "application/json"},
            json=crawl_request.dict(exclude_none=True)
        )
        response.raise_for_status()  # Raise error for HTTP issues

        # Parse the JSON response to get cleaned_html
        json_response = response.json()
        if json_response.get('results'):
            cleaned_html = json_response['results'][0]['cleaned_html']
                    
            # Log the response status and content for debugging
            # print("Crawl4AI response:", response.status_code, cleaned_html)
        else:
            raise HTTPException(status_code=404, detail="No results found")

        # Extract the apartment details from the cleaned HTML
        apartment_details = extract_apartment_details(cleaned_html)  # Using cleaned_html
        # Return the structured response
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
        # Catch all other exceptions for debugging
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

