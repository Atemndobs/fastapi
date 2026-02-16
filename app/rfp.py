from fastapi import APIRouter, HTTPException, status, Query, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from enum import Enum
import logging
import uuid
import httpx
from bs4 import BeautifulSoup
import json

# Add this model for the request body
class RFPUrlRequest(BaseModel):
    url: str = Field(..., description="URL to fetch RFPs from")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of RFPs to return")
    skip: int = Field(0, ge=0, description="Number of RFPs to skip for pagination")

router = APIRouter()
logger = logging.getLogger(__name__)

class RFPCategory(str, Enum):
    WEB_DESIGN = "web-design-and-development-rfp"
    IT = "it-rfp"
    CONSULTING = "consulting-rfp"
    ALL = "all-rfp"

    @classmethod
    def get_default(cls):
        """Return the default category."""
        return cls.WEB_DESIGN

    @classmethod
    def from_url(cls, url: str) -> 'RFPCategory':
        """Determine the category based on URL patterns."""
        if not url:
            return cls.get_default()

        url_lower = url.lower()
        if 'it-rfp' in url_lower or 'it-software' in url_lower:
            return cls.IT
        elif 'consulting' in url_lower:
            return cls.CONSULTING
        elif 'web-design' in url_lower:
            return cls.WEB_DESIGN
        else:
            return cls.get_default()

class RFPCard(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the RFP")
    title: str = Field("", description="Title of the RFP")
    location: str = Field("N/A", description="Location where the RFP is applicable")
    description: str = Field("", description="Detailed description of the RFP")
    posted_date: str = Field("N/A", description="Date when the RFP was posted")
    expiry_date: str = Field("N/A", description="Deadline for the RFP submission")
    url: str = Field("", description="URL to the RFP details page")
    category: str = Field("web-design-and-development", description="Category of the RFP")
    
    @classmethod
    def from_website_data(cls, data: Dict[str, Any]) -> 'RFPCard':
        """Create an RFPCard from website data."""
        # Extract title and clean it up
        title = data.get('title', '').strip()
        if not title and 'name' in data:
            title = data.get('name', '').strip()
            
        # Extract location - try to get it from the data or use a default
        location = 'Not specified'
        if 'location' in data and data['location']:
            location = data['location']
        elif 'address' in data and isinstance(data['address'], dict):
            # Try to construct location from address components
            address_parts = []
            if 'addressLocality' in data['address']:
                address_parts.append(data['address']['addressLocality'])
            if 'addressRegion' in data['address']:
                address_parts.append(data['address']['addressRegion'])
            if 'addressCountry' in data['address']:
                address_parts.append(data['address']['addressCountry'])
            
            if address_parts:
                location = ', '.join(address_parts)
        
        # Handle the case where location might be in a string format
        if isinstance(location, str) and location.startswith('{'):
            try:
                location_data = json.loads(location.replace("'", '"'))
                location = location_data.get('addressLocality', 'Not specified')
            except:
                location = 'Not specified'
        
        # If we still don't have a location, try to extract from description
        if location == 'Not specified' and 'description' in data:
            # Look for location patterns in description
            import re
            location_match = re.search(r'\b(located|based)\s+in\s+([A-Z][a-zA-Z\s,]+)(?:\.|\s|$)', data['description'])
            if location_match:
                location_part = location_match.group(2).strip()
                if location_part and len(location_part) < 50:  # Sanity check
                    location = location_part
        
        # Determine category from URL if available, otherwise use default
        url = data.get('url', '')
        if url:
            category = RFPCategory.from_url(url).value
        else:
            category = RFPCategory.get_default().value
            
        return cls(
            id=data.get('sku', str(uuid.uuid4())),
            title=title,
            location=location,
            description=data.get('description', ''),
            posted_date=data.get('datePosted', 'N/A'),
            expiry_date=data.get('expires', 'N/A'),
            url=url,
            category=category
        )


class RFPDetail(BaseModel):
    """Detailed RFP information model."""
    id: str = Field(..., description="Unique identifier for the RFP")
    title: str = Field(..., description="Title of the RFP")
    description: str = Field(..., description="Detailed description of the RFP")
    scope_of_service: str = Field(..., description="Detailed scope of work/service section")
    posted_date: str = Field(..., description="Date when the RFP was posted")
    expiry_date: str = Field(..., description="Deadline for the RFP submission")
    question_deadline: Optional[str] = Field(None, description="Deadline for questions")
    location: str = Field(..., description="Location where the RFP is applicable")
    budget: Optional[str] = Field(None, description="Budget information if available")
    eligibility: Optional[str] = Field(None, description="Eligibility requirements")
    work_performance: Optional[str] = Field(None, description="Work performance details")
    category: str = Field(..., description="Category of the RFP")
    country: Optional[str] = Field(None, description="Country of the RFP")
    state: Optional[str] = Field(None, description="State/Region of the RFP")

@router.get("/rfps", response_model=List[RFPCard])
async def get_rfps(
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0)
):
    """
    Get a list of RFPs with pagination support.
    
    Args:
        limit: Maximum number of RFPs to return (default: 10, max: 100)
        skip: Number of RFPs to skip (for pagination, default: 0)
    """
    try:
        logger.info(f"Fetching RFPs with limit={limit}, skip={skip}")
        from .rfp_scraper.rfp_scraper import fetch_rfps
        result = await fetch_rfps(limit=limit, skip=skip)
        
        # If we get a dict with items, transform items to RFPCard
        if isinstance(result, dict) and 'items' in result:
            try:
                rfps = [RFPCard.from_website_data(item) for item in result['items']]
                return rfps
            except Exception as e:
                logger.error(f"Error transforming RFP data: {str(e)}", exc_info=True)
                # Fall back to returning raw items if transformation fails
                return []
            
        logger.warning(f"Unexpected result format from fetch_rfps: {result}")
        return []
        
    except Exception as e:
        logger.error(f"Error in get_rfps: {str(e)}", exc_info=True)
        # Return empty list instead of error to prevent 500
        return []

@router.post("/rfps_by_url", response_model=List[RFPCard])
async def get_rfps_by_url(request: RFPUrlRequest = Body(...)):
    """
    Get a list of RFPs from a specific URL with pagination support.
    
    Args (in request body):
        url: The URL to fetch RFPs from
        limit: Maximum number of RFPs to return (default: 10, max: 100)
        skip: Number of RFPs to skip (for pagination, default: 0)
        
    Returns:
        List of RFPCard objects with pagination support
    """
    try:
        logger.info(f"Fetching RFPs from URL: {request.url} with limit={request.limit}, skip={request.skip}")
        from .rfp_scraper.rfp_scraper import fetch_rfps
        
        # Validate URL
        if not request.url.startswith(('http://', 'https://')):
            error_msg = f"Invalid URL. Must start with http:// or https://. Got: {request.url}"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
            
        # Fetch RFPs from the specified URL with pagination
        result = await fetch_rfps(limit=request.limit, skip=request.skip, url=request.url)
        
        # Transform the result to match the expected format
        if isinstance(result, dict) and 'items' in result:
            try:
                rfps = [RFPCard.from_website_data(item) for item in result['items']]
                return rfps
            except Exception as e:
                logger.error(f"Error transforming RFP data: {str(e)}", exc_info=True)
                # Fall back to returning raw items if transformation fails
                return []
                
        logger.warning(f"Unexpected result format from fetch_rfps: {result}")
        return []
        
    except HTTPException as he:
        logger.error(f"HTTP error in get_rfps_by_url: {str(he.detail)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_rfps_by_url: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while fetching RFP details: {str(e)}"
        )

@router.get("/rfp_id")
async def get_rfp_details(
    url: str = Query(..., description="URL of the RFP details page")
):
    """
    Get detailed information about a specific RFP by its URL.
    
    Args:
        url: The complete URL of the RFP details page
        
    Returns:
        Detailed RFP information in the specified format
    """
    try:
        logger.info(f"Fetching RFP details from URL: {url}")
        
        # Extract RFP ID from URL
        rfp_id = ""
        import re
        match = re.search(r'/([A-Za-z0-9-]+)\.html', url)
        if match:
            rfp_id = match.group(1)
        
        # Fetch the RFP details page
        from .rfp_scraper.rfp_scraper import crawl_rfp_details
        rfp_data = await crawl_rfp_details(url)
        
        if not rfp_data:
            raise HTTPException(status_code=404, detail="RFP details not found")
        
        # Extract location from title if available
        location = ""
        title = rfp_data.get('title', '')
        if '(' in title and ')' in title:
            try:
                location = title.split('(')[1].split(')')[0].strip()
                if len(location) > 50:  # Sanity check for location length
                    location = ""
            except:
                pass
        
        # Extract state if location is a 2-letter code
        state = location if location and len(location) == 2 else ""
        
        # Format the response
        formatted_rfp = {
            "id": rfp_id,
            "title": title,
            "description": rfp_data.get('description', ''),
            "scope_of_service": rfp_data.get('scope', rfp_data.get('description', '')),
            "posted_date": rfp_data.get('posted_date', 'N/A'),
            "expiry_date": rfp_data.get('expiry_date', 'N/A'),
            "question_deadline": rfp_data.get('question_deadline'),
            "location": location,
            "budget": rfp_data.get('budget', 'Looking for Proposals'),
            "eligibility": rfp_data.get('eligibility', 'Onshore (USA Organization Only);'),
            "work_performance": rfp_data.get('work_performance', 'Performance of the work will be Offsite.'),
            "category": rfp_data.get('category', 'Web Design and Development, Marketing and Branding, Social Media, Internet Marketing and SEO'),
            "country": rfp_data.get('country', 'USA'),
            "state": state,
            "url": url
        }
        
        return formatted_rfp
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_rfp_details: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch RFP details")

async def extract_section(soup: BeautifulSoup, section_title: str) -> Optional[str]:
    """Extract a specific section from the RFP details page."""
    try:
        # Find the section by the title pattern (e.g., "[*] Scope of Service:")
        section_header = soup.find(lambda tag: tag.name in ['b', 'strong'] and 
                                 section_title.lower() in tag.get_text().lower())
        
        if not section_header:
            return None
            
        # Get the next sibling that contains the content
        content = []
        current = section_header.parent.next_sibling
        
        # Keep collecting content until we hit the next section (marked with [*])
        while current and not (current.name == 'b' and '[*]' in current.get_text()):
            if current.name == 'br':
                content.append('\n')
            elif hasattr(current, 'get_text'):
                text = current.get_text(strip=True)
                if text:
                    content.append(text)
            current = current.next_sibling
        
        # Clean up the content
        section_text = ' '.join(content).strip()
        return section_text if section_text else None
        
    except Exception as e:
        logger.warning(f"Error extracting section '{section_title}': {str(e)}")
        return None

async def _fetch_rfp_details_impl(url: str) -> Dict[str, Any]:
    """
    Internal implementation to fetch and parse detailed RFP data.
    Returns a dictionary containing the detailed RFP information.
    """
    logger.info(f"Fetching RFP details from URL: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.rfpmart.com/',
        'DNT': '1',
        'Connection': 'keep-alive',
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=30.0, follow_redirects=True)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Extract basic information
            title = soup.find('h1').get_text(strip=True) if soup.find('h1') else ""
            
            # Extract posted date
            posted_date = None
            posted_tag = soup.find('b', string=lambda t: t and 'Posted Date' in str(t))
            if posted_tag:
                posted_date = posted_tag.next_sibling.strip(' :')
            
            # Extract expiry date
            expiry_date = None
            expiry_tag = soup.find('b', string=lambda t: t and 'Expiry Date' in str(t))
            if expiry_tag:
                expiry_date = expiry_tag.next_sibling.strip(' :')
            
            # Extract question deadline
            question_deadline = None
            question_tag = soup.find('b', string=lambda t: t and 'Question Answer Deadline' in str(t))
            if question_tag:
                question_deadline = question_tag.next_sibling.strip(' :')
            
            # Extract budget
            budget = None
            budget_tag = soup.find('b', string=lambda t: t and 'Budget:' in str(t))
            if budget_tag:
                budget = budget_tag.next_sibling.strip()
            
            # Extract location, country, state
            location = None
            country = None
            state = None
            location_tag = soup.find('b', string=lambda t: t and 'located in' in str(t).lower())
            if location_tag:
                location_text = location_tag.get_text()
                if ';' in location_text:
                    location = location_text.split(';')[0].replace('located in', '').strip()
                    # Try to extract country and state from location
                    if 'USA' in location_text and '(' in location_text and ')' in location_text:
                        state = location_text.split('(')[1].split(')')[0].strip()
                        country = 'USA'
            
            # Extract category
            category = None
            category_tag = soup.find('b', string='Category :')
            if category_tag:
                category = category_tag.next_sibling.strip()
            
            # Extract scope of service
            scope_of_service = await extract_section(soup, 'Scope of Service')
            
            # Extract eligibility
            eligibility = await extract_section(soup, 'Eligibility')
            
            # Extract work performance
            work_performance = await extract_section(soup, 'Work Performance')
            
            # Extract description (first paragraph)
            description = None
            first_paragraph = soup.find('p')
            if first_paragraph:
                description = first_paragraph.get_text(strip=True)
            
            return {
                "id": rfp_id,
                "title": title,
                "description": description or "",
                "scope_of_service": scope_of_service or "",
                "posted_date": posted_date or "Not specified",
                "expiry_date": expiry_date or "Not specified",
                "question_deadline": question_deadline,
                "location": location or "Not specified",
                "budget": budget,
                "eligibility": eligibility,
                "work_performance": work_performance,
                "category": category or "Not specified",
                "country": country,
                "state": state,
                "url": url
            }
                
    except Exception as e:
        logger.error(f"Error fetching RFP details: {str(e)}", exc_info=True)
        return {"error": f"Error fetching RFP details: {str(e)}"}

async def fetch_rfp_details(rfp_id: str, url: str) -> Dict[str, Any]:
    """
    Fetch detailed RFP information with caching and error handling.
    
    Args:
        rfp_id: The ID of the RFP
        url: The URL of the RFP details page
        
    Returns:
        Dict containing the detailed RFP information
    """
    logger.info(f"Fetching RFP details for ID: {rfp_id} from URL: {url}")
    
    # First try to get from cache if available
    cache_key = f"rfp_detail_{rfp_id}"
    cached_data = cache.get(cache_key)
    if cached_data:
        logger.info(f"Returning cached data for RFP {rfp_id}")
        return {"success": True, "from_cache": True, **cached_data}
    
    try:
        # Try to fetch fresh data
        result = await _fetch_rfp_details_impl(url)
        
        if "error" in result:
            logger.error(f"Error from _fetch_rfp_details_impl: {result['error']}")
            return result
            
        # Cache the successful result
        cache.set(cache_key, result, timeout=3600)  # Cache for 1 hour
        logger.info(f"Successfully fetched and cached RFP details for {rfp_id}")
        
        return {"success": True, "from_cache": False, **result}
        
    except Exception as e:
        error_msg = f"Error in fetch_rfp_details: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"success": False, "error": error_msg}

@router.get("/rfp/{rfp_id}", response_model=RFPDetail)
async def get_rfp_details(rfp_id: str, url: str):
    """
    Get detailed information about a specific RFP by its ID and URL.
    
    Args:
        rfp_id: The ID of the RFP (e.g., 'WD-14716')
        url: The URL of the RFP details page (URL-encoded)
        
    Returns:
        Detailed RFP information with focus on scope of service
    """
    try:
        logger.info(f"Fetching RFP details for ID: {rfp_id} from URL: {url}")
        
        # Validate URL
        if not url.startswith('http'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid URL. Please provide a valid HTTP/HTTPS URL."
            )
        
        # Fetch and parse the RFP details
        result = await fetch_rfp_details(rfp_id, url)
        
        if not result.get("success"):
            error_msg = result.get("error", "Unknown error fetching RFP details")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Failed to fetch RFP details: {error_msg}"
            )
        
        # Remove the success/from_cache fields before creating the response
        rfp_data = {k: v for k, v in result.items() if k not in ["success", "from_cache"]}
        
        # Convert to RFPDetail model
        return RFPDetail(**rfp_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_rfp_details: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching RFP details: {str(e)}"
        )


@router.get("/rfps/search", response_model=List[RFPCard])
async def search_rfps(
    query: Optional[str] = None,
    location: Optional[str] = None,
    limit: int = 10,
    skip: int = 0
):
    """
    Search RFPs with filters.
    
    Args:
        query: Text to search in title or description
        location: Location to filter by
        limit: Maximum number of results to return
        skip: Number of results to skip
    """
    try:
        from .rfp_scraper.rfp_scraper import fetch_rfps
        
        # Get all RFPs (up to 1000) and filter in memory
        rfps = await fetch_rfps(limit=1000, skip=0)
        
        # Apply filters
        if query:
            query = query.lower()
            rfps = [r for r in rfps if query in r.title.lower() or query in r.description.lower()]
            
        if location:
            location = location.lower()
            rfps = [r for r in rfps if location in r.location.lower() or location in r.title.lower()]
        
        # Apply pagination
        return rfps[skip:skip + limit]
        
    except Exception as e:
        logger.error(f"Error searching RFPs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching RFPs: {str(e)}"
        )

@router.get("/rfps/{rfp_id}", response_model=RFPCard)
async def get_rfp(rfp_id: str):
    """
    Get details of a specific RFP by ID.
    
    Args:
        rfp_id: The ID of the RFP to retrieve
    """
    try:
        from .rfp_scraper.rfp_scraper import fetch_rfps
        
        # Fetch all RFPs and find the one with matching ID
        rfps = await fetch_rfps(limit=1000)
        rfp = next((r for r in rfps if r.id == rfp_id), None)
        if rfp:
            return rfp
                
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RFP with ID {rfp_id} not found"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching RFP {rfp_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching RFP: {str(e)}"
        )
