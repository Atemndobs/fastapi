# models.py

from pydantic import BaseModel
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

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
    num_stops: int 

class TransitInfo(ModeDistance):
    transit_details: List[TransitDetails]

class DistanceResponse(BaseModel):
    driving: ModeDistance
    walking: ModeDistance
    bicycling: ModeDistance
    transit: TransitInfo


    # Define AddToListRequest model

class AddToListRequest(BaseModel):
    address: str
    target_address: str
    platform: str
    appart_url: str
    id: Optional[str] = None
    urls: Optional[List[str]] = None
    include_raw_html: Optional[bool] = False
    bypass_cache: Optional[bool] = False
    extract_blocks: Optional[bool] = False
    word_count_threshold: Optional[int] = None
    extraction_strategy: Optional[str] = None
    extraction_strategy_args: Optional[Dict[str, str]] = None
    chunking_strategy: Optional[str] = None
    chunking_strategy_args: Optional[Dict[str, str]] = None
    css_selector: Optional[str] = None
    screenshot: Optional[bool] = False
    user_agent: Optional[str] = None
    verbose: Optional[bool] = False