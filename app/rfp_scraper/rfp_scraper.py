# Standard library imports
import asyncio
import datetime
import hashlib
import json
import logging
import os
import random
import re
import sys
import traceback
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

# Third-party imports
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Query, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
from pydantic import BaseModel, Field, HttpUrl
import requests

# Local application imports
from ..models import CrawlRequest
from ..utils import crawl_url

# Configure logging
logger = logging.getLogger(__name__)

# Create debug directory if it doesn't exist
os.makedirs('debug', exist_ok=True)

def save_debug_data(prefix: str, data: Any, extension: str = 'html') -> str:
    """Save debug data to a file."""
    try:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'debug/{prefix}_{timestamp}.{extension}'
        
        if isinstance(data, (dict, list, tuple)) and extension == 'json':
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            if not isinstance(data, str):
                data = str(data)
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(data)
                
        logger.info(f"Saved debug data to {filename}")
        return filename
    except Exception as e:
        logger.error(f"Failed to save debug data: {e}")
        return ""

def create_app() -> FastAPI:
    app = FastAPI(
        title="RFP Scraper API",
        description="API for scraping RFP data from rfpmart.com",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )

    # Enable CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add startup event
    @app.on_event("startup")
    async def startup_event():
        logger.info("Starting RFP Scraper API...")

    # Add exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error"},
        )

    return app

app = create_app()

class RFPCategory(str, Enum):
    WEB_DESIGN = "web-design-and-development"
    IT_SOFTWARE = "it-software"
    MOBILE_APPS = "mobile-apps"
    MOBILE_DESIGN = "mobile-design"
    GRAPHICS = "graphics-multimedia"
    SEO = "seo"
    CONTENT_WRITING = "content-writing"
    DIGITAL_MARKETING = "digital-marketing"
    OTHER = "other"

    @classmethod
    def get_default(cls):
        """Return the default category to use when none is specified."""
        return cls.WEB_DESIGN
        
    @classmethod
    def from_url(cls, url: str) -> 'RFPCategory':
        """
        Determine the category based on URL patterns.
        
        Args:
            url: The URL to analyze
            
        Returns:
            RFPCategory: The detected category, or default if not found
        """
        if not url:
            return cls.get_default()
            
        url = url.lower()
        
        # Check for mobile-related patterns first
        if any(term in url for term in ['/mobile-app', 'mobile-apps', 'mobileapp', 'mobile-application', 'ios-app', 'android-app', 'flutter-app']):
            return cls.MOBILE_APPS
            
        if any(term in url for term in ['mobile-design', 'mobile-ui', 'mobile-ux']):
            return cls.MOBILE_DESIGN
            
        # Check for other categories
        category_mapping = {
            'web-design': cls.WEB_DESIGN,
            'it-software': cls.IT_SOFTWARE,
            'graphics': cls.GRAPHICS,
            'seo': cls.SEO,
            'content': cls.CONTENT_WRITING,
            'marketing': cls.DIGITAL_MARKETING
        }
        
        for term, category in category_mapping.items():
            if term in url:
                return category
                
        return cls.get_default()

class RFPCard(BaseModel):
    id: str = Field(..., description="Unique identifier for the RFP")
    title: str = Field(..., description="Title of the RFP")
    location: str = Field(..., description="Location where the RFP is applicable")
    description: str = Field(..., description="Detailed description of the RFP")
    posted_date: str = Field(..., description="Date when the RFP was posted")
    expiry_date: str = Field(..., description="Deadline for the RFP submission")
    url: str = Field(..., description="URL to the RFP details page")
    category: str = Field(..., description="Category of the RFP")

class RFPSearchParams(BaseModel):
    query: Optional[str] = None
    location: Optional[str] = None
    category: Optional[RFPCategory] = RFPCategory.WEB_DESIGN
    min_budget: Optional[float] = None
    max_budget: Optional[float] = None
    posted_after: Optional[str] = None
    expires_before: Optional[str] = None

async def fetch_html(url: str, max_retries: int = 3, backoff_factor: float = 1.0) -> Optional[str]:
    """
    Fetch HTML content from a URL with retry logic and robust error handling.
    
    Args:
        url: The URL to fetch
        max_retries: Maximum number of retry attempts (default: 3)
        backoff_factor: Multiplier for exponential backoff between retries (default: 1.0)
        
    Returns:
        str: The HTML content if successful, None otherwise
    """
    # Normalize URL
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = f'https://{url.lstrip("/")}'
    
    # Rotating user agents to reduce chance of being blocked
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15'
    ]
    
    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
        'Referer': 'https://www.google.com/',
        'DNT': '1',
    }
    
    # Configure client with connection pooling and retry logic
    # Using simpler configuration for better compatibility
    client_params = {
        'timeout': 30.0,
        'follow_redirects': True,
        'http2': True,
        'headers': headers,
        'verify': False  # Skip SSL verification if needed
    }
    
    # Add limits if available in the current httpx version
    try:
        client_params['limits'] = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    except (AttributeError, TypeError):
        logger.warning("httpx.Limits not available, using default connection settings")
    
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            # Rotate user agent for each attempt
            headers['User-Agent'] = random.choice(user_agents)
            
            # Add a random delay between retries
            if attempt > 0:
                delay = min(backoff_factor * (2 ** (attempt - 1)) + random.uniform(0, 1), 10)
                logger.info(f"Attempt {attempt + 1}/{max_retries} - Waiting {delay:.2f}s before retry...")
                await asyncio.sleep(delay)
            else:
                logger.info(f"Fetching URL: {url}")
            
            # Create a new client for each attempt to avoid connection pool issues
            try:
                async with httpx.AsyncClient(**client_params) as client:
                    # Make the request with timeout
                    response = await client.get(url, timeout=30.0)
            except Exception as e:
                last_error = f"HTTP client error: {str(e)}"
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {last_error}")
                if attempt == max_retries - 1:  # If this was the last attempt
                    logger.error(f"All {max_retries} attempts failed for {url}")
                    return None
                continue
                
                # Check for rate limiting (HTTP 429)
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 5))
                    logger.warning(f"Rate limited. Retrying after {retry_after} seconds...")
                    await asyncio.sleep(retry_after)
                    continue
                
                # Check for other error status codes
                response.raise_for_status()
                
                # Check if we got a valid HTML response
                content_type = response.headers.get('content-type', '')
                if 'text/html' not in content_type:
                    raise ValueError(f"Unexpected content type: {content_type}")
                
                # Check for common anti-scraping measures
                html = response.text
                if any(term in html.lower() for term in ['access denied', 'cloudflare', 'captcha', 'security check']):
                    raise ValueError("Anti-scraping measures detected in response")
                    
                return html
                
                
        except httpx.HTTPStatusError as e:
            last_error = e
            status_code = e.response.status_code if e.response else "unknown"
            logger.warning(f"HTTP error {status_code} on attempt {attempt + 1}: {str(e)}")
            
            # Don't retry on client errors (4xx) except 429 (handled above) and 408 (timeout)
            if 400 <= status_code < 500 and status_code not in (408, 429):
                logger.error(f"Client error {status_code}, not retrying")
                break
                
        except httpx.RequestError as e:
            last_error = e
            logger.warning(f"Request error on attempt {attempt + 1}: {str(e)}")
            
        except Exception as e:
            last_error = e
            logger.error(f"Unexpected error on attempt {attempt + 1}: {str(e)}", exc_info=True)
            
        # Calculate backoff with jitter
        if attempt < max_retries - 1:
            backoff = min(backoff_factor * (2 ** attempt), 30)  # Cap at 30 seconds
            jitter = 0.5 + (random.random() * 0.5)  # Random between 0.5 and 1.0
            sleep_time = backoff * jitter
            logger.info(f"Retrying in {sleep_time:.1f} seconds... (attempt {attempt + 1}/{max_retries})")
            await asyncio.sleep(sleep_time)
    
    # If we get here, all retries failed
    error_msg = f"Failed to fetch {url} after {max_retries} attempts"
    if last_error:
        error_msg += f": {str(last_error)}"
    logger.error(error_msg)
    
    # Raise appropriate HTTP exception based on the last error
    if isinstance(last_error, httpx.HTTPStatusError):
        if last_error.response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Page not found: {url}"
            ) from last_error
        else:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch {url}: {str(last_error)}"
            ) from last_error
    elif isinstance(last_error, httpx.RequestError):
        raise HTTPException(
            status_code=503,
            detail=f"Service unavailable while fetching {url}: {str(last_error)}"
        ) from last_error
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error while fetching {url}"
        ) from last_error

async def parse_rfp_page(html: str, category: str = "") -> List[RFPCard]:
    """
    Parse the HTML content of an RFP listing page and extract RFP details.
    
    Args:
        html: The HTML content to parse
        category: The RFP category (for reference)
        
    Returns:
        List[RFPCard]: A list of parsed RFP cards
    """
    # Save HTML for debugging
    debug_file = save_debug_data('rfp_page_raw', html)
    logger.info(f"Saved raw HTML to {debug_file}")
    
    # Parse the HTML with BeautifulSoup
    soup = BeautifulSoup(html, 'lxml')
    
    # Remove script and style elements to clean up the HTML
    for script in soup(['script', 'style', 'noscript', 'meta', 'link', 'nav', 'header', 'footer']):
        script.decompose()
    
    # Save cleaned HTML for debugging
    cleaned_html = str(soup)
    save_debug_data('rfp_page_cleaned', cleaned_html)
    
    # Common patterns for RFP containers on RFP Mart
    container_selectors = [
        # Main content areas
        '.rfp-listings', '.rfp-container', '.rfp-items',
        '.content-area', '.main-content', '#main',
        # Grid/List containers
        '.items-container', '.list-view', '.grid-view',
        # Generic containers with multiple children
        'div[class*="rfp"]', 'div[class*="list"]', 'div[class*="item"]',
        'section', 'article', 'ul', 'ol', 'div'
    ]
    
    # Try to find the main container with RFP items
    container = None
    for selector in container_selectors:
        try:
            elements = soup.select(selector)
            # Look for containers with multiple similar children
            for elem in elements:
                children = [c for c in elem.find_all(recursive=False) 
                           if c.name and c.name not in ['script', 'style']]
                
                # Check if this looks like an RFP container
                if len(children) >= 3:  # At least 3 potential items
                    # Look for common RFP patterns in the container
                    has_titles = bool(elem.select('h2, h3, h4, .title, [class*="title"]'))
                    has_descriptions = bool(elem.select('p, .description, [class*="desc"]'))
                    has_dates = bool(re.search(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+\d{1,4}\b', 
                                              elem.get_text(), re.IGNORECASE))
                    
                    if has_titles and (has_descriptions or has_dates):
                        container = elem
                        logger.info(f"Found container with {len(children)} potential items using selector: {selector}")
                        break
                        
            if container:
                break
                
        except Exception as e:
            logger.debug(f"Error with container selector {selector}: {e}")
    
    if not container:
        logger.warning("No suitable container found, using entire document")
        container = soup
    
    # Save container HTML for debugging
    save_debug_data('rfp_container', str(container))
    
    # Find potential RFP items - ordered by specificity
    item_selectors = [
        # Specific RFP item selectors
        '.rfp-item', '.rfp-entry', '.rfp-card',
        # Common item classes
        '.post-item', '.post-card', '.entry-card',
        '.card', '.item', '.listing-item',
        # Structural patterns
        'article', 'section', 'li',
        'div[class*="item"]', 'div[class*="entry"]', 'div[class*="card"]',
        # Fallback to any div with multiple children and text
        'div:has(> h2, > h3, > h4, > .title, > [class*="title"])',
        'div:has(> a[href]):has(> p, > div, > span)'
    ]
    
    rfp_items = []
    for selector in item_selectors:
        try:
            items = container.select(selector)
            if items:
                logger.info(f"Found {len(items)} potential items with selector: {selector}")
                rfp_items = items
                break
        except Exception as e:
            logger.debug(f"Error with item selector {selector}: {e}")
    
    # If no items found with standard selectors, try fallback method
    if not rfp_items:
        logger.warning("No items found with standard selectors, trying fallback method")
        # Look for elements that look like RFP items based on content
        potential_items = []
        for elem in container.find_all(recursive=True):
            # Skip elements that are too small or too large
            text = elem.get_text(strip=True)
            if len(text) < 50 or len(text) > 5000:
                continue
                
            # Look for elements with title-like text and some content
            title_elem = elem.find(['h2', 'h3', 'h4', 'strong', 'b'])
            has_link = bool(elem.find('a'))
            has_date = bool(re.search(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+\d{1,4}\b', 
                                     text, re.IGNORECASE))
            
            if (title_elem or has_link) and (len(text.split()) > 10 or has_date):
                potential_items.append(elem)
                
        if potential_items:
            logger.info(f"Found {len(potential_items)} potential items with fallback method")
            rfp_items = potential_items
    
    if not rfp_items:
        logger.warning("No RFP items found in the page")
        return []
        
    logger.info(f"Found {len(rfp_items)} potential RFP items in the HTML")
    
    # Parse each RFP item
    parsed_rfps = []
    for item in rfp_items:
        try:
            # Save item HTML for debugging
            item_id = str(uuid.uuid4())[:8]
            save_debug_data(f'rfp_item_{item_id}', str(item))
            
            # Extract title
            title = ""
            title_elem = item.find(['h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'b', '.title', '[class*="title"]'])
            if title_elem:
                title = title_elem.get_text(' ', strip=True)
            
            # If no title found, try to extract from link text
            if not title:
                link_elem = item.find('a')
                if link_elem and link_elem.get_text(strip=True):
                    title = link_elem.get_text(' ', strip=True)
            
            # If still no title, try to find the largest text node
            if not title:
                text_nodes = [t for t in item.find_all(string=True) if t.strip()]
                if text_nodes:
                    # Get the longest text that's not too long
                    text_nodes = [t for t in text_nodes if 10 < len(t) < 200]
                    if text_nodes:
                        title = max(text_nodes, key=len).strip()
            
            # Clean up the title
            if title:
                title = ' '.join(title.split())  # Normalize whitespace
                title = title[:200]  # Limit length
            
            # Extract URL
            url = "#"
            link_elem = item.find('a', href=True)
            if link_elem:
                url = link_elem['href'].strip()
                # Make URL absolute if it's relative
                if url.startswith('/'):
                    url = f"https://www.rfpmart.com{url}"
                elif not url.startswith(('http://', 'https://')):
                    url = f"https://www.rfpmart.com/{url.lstrip('/')}"
            
            # Extract ID from URL or generate one
            rfp_id = ""
            if url and url != "#":
                # Try to extract ID from URL
                id_match = re.search(r'/([^/]+?)(?:\?|$)', url)
                if id_match:
                    rfp_id = id_match.group(1)
            
            # Generate ID if not found
            if not rfp_id:
                import hashlib
                rfp_id = f"rfp_{hashlib.md5((title or str(uuid.uuid4())).encode()).hexdigest()[:8]}"
            
            # Extract location (if present in title)
            location = ""
            if title:
                loc_match = re.search(r'\((.*?)\)', title)
                if loc_match:
                    location = loc_match.group(1).strip()
            
            # Extract dates
            posted_date = ""
            expiry_date = ""
            
            # Look for date patterns in the item text
            date_text = item.get_text()
            date_matches = re.findall(
                r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[\s,]+(\d{1,2})(?:[\s,]+(\d{4}))?\b', 
                date_text, 
                re.IGNORECASE
            )
            
            if date_matches:
                if len(date_matches) >= 2:
                    posted_date = ' '.join(filter(None, date_matches[0]))
                    expiry_date = ' '.join(filter(None, date_matches[1]))
                else:
                    expiry_date = ' '.join(filter(None, date_matches[0]))
            
            # Extract description
            description = ""
            # First try to find a description element
            desc_elem = item.select_one('.description, .summary, p, [class*="desc"], [class*="content"]')
            if desc_elem:
                description = desc_elem.get_text(' ', strip=True)
            else:
                # If no dedicated description, use all text content
                text_content = item.get_text(' ', strip=True)
                # Remove title and dates to avoid duplication
                if title and title in text_content:
                    text_content = text_content.replace(title, '').strip()
                if posted_date and posted_date in text_content:
                    text_content = text_content.replace(posted_date, '').strip()
                if expiry_date and expiry_date in text_content:
                    text_content = text_content.replace(expiry_date, '').strip()
                description = ' '.join(text_content.split())  # Normalize whitespace
            
            # Clean up the description
            if description:
                description = re.sub(r'\s+', ' ', description).strip()
                description = description[:1000]  # Limit length
            
            # Create the RFP card
            card = RFPCard(
                id=rfp_id,
                title=title or "Untitled RFP",
                location=location,
                description=description or "No description available",
                posted_date=posted_date or "Not specified",
                expiry_date=expiry_date or "Not specified",
                url=url,
                category=category
            )
            
            parsed_rfps.append(card)
            logger.debug(f"Parsed RFP: {card.id} - {card.title}")
            
        except Exception as e:
            logger.error(f"Error parsing RFP item: {str(e)}", exc_info=True)
            continue
    
    logger.info(f"Successfully parsed {len(parsed_rfps)} RFP cards")
    return parsed_rfps
    
    # Parse each potential RFP card
    cards = []
    for card in rfp_cards:
        try:
            # Save card HTML for debugging
            card_id = str(uuid.uuid4())[:8]
            save_debug_data(f'rfp_card_{card_id}', str(card))
            
            # Extract title - try multiple possible selectors and locations
            title = ""
            
            # First try to find a title element
            for selector in ['h1', 'h2', 'h3', 'h4', '.title']:
                title_elem = card.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(' ', strip=True)
                    if len(title) > 10:  # Only use if it's substantial text
                        break
            
            # If no title found, try to find the largest text in the card
            if not title:
                text_elements = card.find_all(string=True, recursive=True)
                text_elements = [t.strip() for t in text_elements if t.strip()]
                if text_elements:
                    # Get the longest text that's not too long (to avoid getting the whole content)
                    text_elements = [t for t in text_elements if 10 < len(t) < 200]
                    if text_elements:
                        title = max(text_elements, key=len)
            
            # Clean up the title
            if title:
                title = ' '.join(title.split())  # Normalize whitespace
                title = title[:200]  # Limit length
            
            # Extract URL - try multiple approaches
            link = "#"
            
            # First try to find a link in the card
            link_elems = card.select('a[href]')
            
            # Prefer links that have text content (not just icons or images)
            for link_elem in link_elems:
                if 'href' in link_elem.attrs:
                    href = link_elem['href'].strip()
                    if not href or href == '#':
                        continue
                        
                    # Check if this looks like a valid RFP link
                    if any(x in href.lower() for x in ['rfp', 'tender', 'bid', 'proposal', 'project']):
                        link = href
                        break
                    
                    # If the link has text content, it's probably a good candidate
                    link_text = link_elem.get_text(strip=True)
                    if len(link_text) > 10:  # Only consider if it has substantial text
                        link = href
                        break
            
            # If no good link found, use the first link
            if link == "#" and link_elems and 'href' in link_elems[0].attrs:
                link = link_elems[0]['href'].strip()
            
            # Make sure the link is absolute and clean
            if link and link != "#":
                link = link.split('#')[0]  # Remove fragment
                if link.startswith('//'):  # Protocol-relative URL
                    link = f"https:{link}"
                elif link.startswith('/'):  # Root-relative URL
                    link = f"https://www.rfpmart.com{link}"
                elif not link.startswith(('http://', 'https://')):  # Relative URL
                    link = f"https://www.rfpmart.com/{link.lstrip('/')}"
            
            # Extract ID from URL or title if possible
            rfp_id = link.split('/')[-1] or str(uuid.uuid4())[:8]
            id_patterns = [
                r'(WD-\d+-[A-Za-z-]+)',  # WD-12345-USA
                r'(RFP-\d+-[A-Za-z-]+)',  # RFP-12345-USA
                r'(\d{4,}-[A-Za-z-]+)',   # 12345-USA
                r'(\b[A-Z]{2,}-\d+-[A-Z]+\b)'  # WD-12345-USA (alternative pattern)
            ]
            
            for pattern in id_patterns:
                id_match = re.search(pattern, title or link)
                if id_match:
                    rfp_id = id_match.group(1)
                    break
            
            # If no ID found in title, try to extract from URL
            if not rfp_id and url:
                for pattern in id_patterns:
                    id_match = re.search(pattern, url)
                    if id_match:
                        rfp_id = id_match.group(1)
                        break
            
            # If still no ID, generate a hash from the title
            if not rfp_id:
                import hashlib
                rfp_id = f"RFP-{hashlib.md5(title.encode()).hexdigest()[:8]}"
            
            # Extract location (usually in parentheses in the title)
            location = ""
            loc_match = re.search(r'\((.*?)\)', title)
            if loc_match:
                location = loc_match.group(1)
            
            # Extract dates (posted and expiry)
            posted_date = ""
            expiry_date = ""
            
            # Try to find date elements - these selectors might need adjustment
            date_elements = item.select('.date, .rfp-date, .posted-date, .expiry-date, .deadline')
            date_texts = [elem.get_text(strip=True) for elem in date_elements]
            
            # Look for posted date patterns
            for text in date_texts:
                if 'posted' in text.lower():
                    posted_date = re.sub(r'(?i)posted\s*[:\s]*', '', text, flags=re.IGNORECASE).strip()
                elif 'expir' in text.lower() or 'deadline' in text.lower():
                    expiry_date = re.sub(r'(?i)(expir|deadline)\s*[:\s]*', '', text, flags=re.IGNORECASE).strip()
            
            # If no dates found, try to extract from text
            if not posted_date or not expiry_date:
                date_matches = re.findall(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+\d{1,2}[\s,]*\d{4}\b', 
                                        item.get_text(), re.IGNORECASE)
                if date_matches:
                    if len(date_matches) >= 2:
                        posted_date, expiry_date = date_matches[0], date_matches[1]
                    else:
                        expiry_date = date_matches[0]
            
            # Extract description
            description = ""
            desc_elem = item.select_one('.description, .rfp-desc, .summary, p')
            if desc_elem:
                description = desc_elem.get_text(strip=True, separator=' ')
            else:
                # If no dedicated description element, take all text content
                # but remove the title and dates to avoid duplication
                text_content = item.get_text(separator=' ', strip=True)
                if title in text_content:
                    text_content = text_content.replace(title, '').strip()
                for date_text in date_texts:
                    if date_text in text_content:
                        text_content = text_content.replace(date_text, '').strip()
                description = ' '.join(text_content.split())  # Normalize whitespace
            
            # Clean up the description
            description = re.sub(r'\s+', ' ', description).strip()
            
            # Create the RFP card
            card = RFPCard(
                id=rfp_id,
                title=title,
                location=location,
                description=description,
                posted_date=posted_date,
                expiry_date=expiry_date,
                url=url,
                category=category
            )
            
            cards.append(card)
            logger.debug(f"Parsed RFP: {card.id} - {card.title}")
            
        except Exception as e:
            logger.error(f"Error parsing RFP card: {str(e)}", exc_info=True)
            continue
    
    logger.info(f"Successfully parsed {len(cards)} RFP cards")
    return cards

async def parse_rfp_page_fallback(html: str, category: str = "") -> List[RFPCard]:
    """
    Alternative parsing function that tries different approaches to extract RFP data.
    This is used when the main parsing function fails to find any RFPs.
    
    Args:
        html: The HTML content to parse
        category: The RFP category (for reference)
        
    Returns:
        List[RFPCard]: A list of parsed RFP cards
    """
    logger.info("Trying fallback parsing strategy...")
    
    try:
        soup = BeautifulSoup(html, 'lxml')
        
        # Try to find any potential RFP containers using more generic selectors
        containers = []
        
        # Try different container selectors
        for selector in [
            'div[class*="item"]', 
            'div[class*="card"]', 
            'div[class*="post"]',
            'article', 
            'section',
            'li',
            'div > div',
            'div[class*="list"] > *',
            'div[class*="grid"] > *'
        ]:
            items = soup.select(selector)
            if items:
                logger.info(f"Found {len(items)} items with selector: {selector}")
                containers.extend(items)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_containers = []
        for item in containers:
            item_str = str(item)
            if item_str not in seen:
                seen.add(item_str)
                unique_containers.append(item)
        
        logger.info(f"Found {len(unique_containers)} unique potential RFP containers")
        
        # Parse each container as a potential RFP
        rfp_cards = []
        for idx, container in enumerate(unique_containers[:50]):  # Limit to first 50 to avoid excessive processing
            try:
                # Extract basic information
                title_elem = container.find(['h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'b', '.title', '[class*="title"]'])
                title = title_elem.get_text(' ', strip=True) if title_elem else f"RFP {idx + 1}"
                
                # Try to find a link
                link = "#"
                link_elem = container.find('a', href=True)
                if link_elem:
                    link = link_elem['href']
                    if link.startswith('/'):
                        link = f"https://www.rfpmart.com{link}"
                    elif not link.startswith(('http://', 'https://')):
                        link = f"https://www.rfpmart.com/{link.lstrip('/')}"
                
                # Generate a simple ID
                rfp_id = f"fallback_{hash(str(container))[:8]}"
                
                # Create a basic RFP card
                card = RFPCard(
                    id=rfp_id,
                    title=title[:200],
                    location="",
                    description=container.get_text(' ', strip=True)[:500],
                    posted_date="Not specified",
                    expiry_date="Not specified",
                    url=link,
                    category=category
                )
                rfp_cards.append(card)
                
            except Exception as e:
                logger.debug(f"Error parsing fallback container {idx + 1}: {str(e)}")
                continue
        
        logger.info(f"Successfully parsed {len(rfp_cards)} RFP cards using fallback method")
        return rfp_cards
        
    except Exception as e:
        logger.error(f"Error in fallback parsing: {str(e)}", exc_info=True)
        return []

async def _fetch_rfps_impl(url: str = None) -> Dict[str, Any]:
    """
    Internal implementation to fetch and parse RFP data.
    
    Args:
        url: The URL to fetch RFPs from. If not provided, uses a default URL.
        
    Returns:
        Dictionary containing all items from @itemListElement.
    """
    # Use provided URL or fall back to default
    target_url = url or "https://www.rfpmart.com/web-design-and-development-rfp-government-contract.html"
    logger.info(f"Fetching RFPs from URL: {target_url}")
    
    try:
        # Make a GET request to the target URL
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.rfpmart.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
        }
        
        # Make the request
        async with httpx.AsyncClient() as client:
            response = await client.get(
                target_url,
                headers=headers,
                timeout=30.0,
                follow_redirects=True
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch {target_url}. Status code: {response.status_code}")
                return {"error": f"Failed to fetch data. Status code: {response.status_code}"}
            
            html = response.text
            
            # Save the HTML for debugging
            debug_file = save_debug_data('rfp_listing', html)
            logger.info(f"Saved RFP listing HTML to {debug_file}")
            
            # Parse the JSON-LD data from the HTML
            soup = BeautifulSoup(html, 'lxml')
            script_tag = soup.find('script', type='application/ld+json')
            
            if not script_tag:
                logger.error("No JSON-LD data found in the HTML")
                return {"error": "No JSON-LD data found in the HTML"}
            
            try:
                # Get JSON string and parse with strict=False to allow control characters in strings
                # The website has malformed JSON with unescaped tabs inside string values
                json_string = script_tag.string

                # Parse the JSON-LD data with strict=False to tolerate control characters
                json_data = json.loads(json_string, strict=False)
                
                # Extract the item list
                if "@itemListElement" not in json_data:
                    logger.error("No itemListElement found in JSON-LD data")
                    return {"error": "No itemListElement found in JSON-LD data"}
                
                # Process items to remove the 'offers' field
                def clean_item(item_data):
                    if not isinstance(item_data, dict):
                        return item_data
                    # Create a new dict without the 'offers' field
                    return {k: v for k, v in item_data.items() if k != 'offers'}

                # Determine the target category from the URL
                target_category = RFPCategory.from_url(target_url)
                logger.info(f"Target category from URL: {target_category.value}")

                # Get all items from @itemListElement
                all_items = [clean_item(item.get("item", {})) for item in json_data["@itemListElement"]]

                # Filter items based on the target category
                # Only filter if not using web-design (default) category, to maintain backward compatibility
                if target_category != RFPCategory.WEB_DESIGN:
                    filtered_items = []
                    for item in all_items:
                        item_url = item.get('url', '')
                        item_category = RFPCategory.from_url(item_url)
                        # Include item if its category matches the target category
                        if item_category == target_category:
                            filtered_items.append(item)
                    items = filtered_items
                    logger.info(f"Filtered to {len(items)} items matching category {target_category.value}")
                else:
                    items = all_items

                result = {
                    "success": True,
                    "count": len(items),
                    "items": items,
                    "metadata": {
                        "source": target_url,
                        "retrieved_at": datetime.datetime.utcnow().isoformat(),
                        "total_items": len(items)
                    }
                }
                
                logger.info(f"Successfully extracted {result['count']} items from @itemListElement")
                return result
                
            except json.JSONDecodeError as e:
                error_msg = f"Error parsing JSON-LD data: {str(e)}"
                logger.error(error_msg)
                return {"error": error_msg, "success": False}
            
    except Exception as e:
        error_msg = f"Error in _fetch_rfps_impl: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"error": error_msg, "success": False}

async def fetch_rfps(limit: int = 10, skip: int = 0, url: str = None) -> Dict[str, Any]:
    """
    Get a list of RFPs with pagination support.
    
    Args:
        limit: Maximum number of items to return
        skip: Number of items to skip for pagination
        url: Optional URL to fetch RFPs from. If not provided, uses default URL.
        
    Returns:
        Dictionary containing the RFP data and pagination info
    """
    logger.info(f"Fetching {limit} RFPs (skip: {skip})")
    
    try:
        # Fetch fresh data
        logger.info("Fetching RFP data...")
        result = await _fetch_rfps_impl(url=url)
        
        # If fetch failed, return error response
        if not result.get('success', False):
            logger.warning(f"Failed to fetch RFP data: {result.get('error', 'Unknown error')}")
            return {
                "success": False,
                "count": 0,
                "items": [],
                "pagination": {
                    "total": 0,
                    "limit": limit,
                    "skip": skip,
                    "has_more": False
                },
                "metadata": {"source": "error", "error": result.get('error', 'Unknown error')}
            }
        
        # Apply pagination to the items
        items = result.get('items', [])
        total_items = len(items)
        end_idx = min(skip + limit, total_items)
        
        # Create the paginated response
        paginated_result = {
            "success": True,
            "count": min(limit, max(0, total_items - skip)),
            "items": items[skip:end_idx],
            "pagination": {
                "total": total_items,
                "limit": limit,
                "skip": skip,
                "has_more": (skip + limit) < total_items
            },
            "metadata": result.get('metadata', {})
        }
        
        return paginated_result
        
    except Exception as e:
        error_msg = f"Error in fetch_rfps: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "count": 0,
            "items": [],
            "pagination": {
                "total": 0,
                "limit": limit,
                "skip": skip,
                "has_more": False
            },
            "metadata": {"source": "error", "error": str(e)}
        }

# The POST /rfps endpoint has been moved to rfp.py

@app.get("/rfps/search", response_model=List[RFPCard])
async def search_rfps(
    query: Optional[str] = None,
    location: Optional[str] = None,
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0)
):
    """
    Search RFPs with filters
    
    Args:
        query: Text to search in title or description
        location: Location to filter by
        limit: Maximum number of results to return
        skip: Number of results to skip
    """
    try:
        # Get all RFPs and apply filters
        result = await fetch_rfps(limit=1000, skip=0)
        
        if not result.get('success', False):
            raise HTTPException(
                status_code=500,
                detail=result.get('error', 'Unknown error searching RFPs')
            )
            
        items = result.get('items', [])
        
        # Apply search filters
        if query:
            query = query.lower()
            items = [item for item in items 
                    if query in item.get('title', '').lower() 
                    or query in item.get('description', '').lower()]
                    
        if location:
            location = location.lower()
            items = [item for item in items 
                    if location in item.get('location', '').lower() 
                    or location in item.get('title', '').lower()]
        
        # Apply pagination
        total = len(items)
        paginated_items = items[skip:skip + limit]
        
        return {
            "success": True,
            "count": len(paginated_items),
            "items": paginated_items,
            "pagination": {
                "total": total,
                "limit": limit,
                "skip": skip,
                "has_more": (skip + limit) < total
            },
            "metadata": result.get('metadata', {})
        }
    except Exception as e:
        error_msg = f"Error in search_rfps: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/rfp/{rfp_id}")
async def get_rfp(rfp_id: str, url: str = Query(..., description="URL of the RFP details page")):
    """
    Get details of a specific RFP by ID and URL
    
    Args:
        rfp_id: The ID of the RFP
        url: The URL of the RFP details page (URL-encoded)
        
    Returns:
        Detailed RFP information
    """
    try:
        # Validate URL
        if not url.startswith('http'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid URL. Please provide a valid HTTP/HTTPS URL."
            )
        
        # Fetch RFP details using the crawler service
        rfp_data = await crawl_rfp_details(url)
        
        # Ensure the ID in the response matches the requested ID
        rfp_data['id'] = rfp_id
        
        return rfp_data
        
    except HTTPException as he:
        # Re-raise HTTP exceptions as is
        raise he
    except Exception as e:
        error_msg = f"Error fetching RFP details: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

async def crawl_rfp_details(url: str) -> Dict[str, Any]:
    """
    Fetch RFP details using the crawler service.
    
    Args:
        url: The URL of the RFP details page
        
    Returns:
        Dict containing the parsed RFP details
    """
    logger.info(f"[CRAWL] Starting crawl for RFP URL: {url}")
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[CRAWL:{request_id}] Request initiated")
    
    # Initialize variables
    scope_text = None
    end_marker = None
    
    try:
        # Create a crawl request similar to crawl_apartment_data
        from app.models import CrawlRequest

        crawl_request = CrawlRequest(
            address="",  # Not used for RFP crawling
            platform="rfp",
            appart_url=url,
            id=request_id,
            target_address="",  # Not used for RFP crawling
            urls=[url],
            extract_blocks=True,
            word_count_threshold=5,
            extraction_strategy="NoExtractionStrategy",
            chunking_strategy="RegexChunking"
        )

        # Make request to the crawl service
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://scrape.cloud.atemkeng.de/crawl",
                headers={"Content-Type": "application/json"},
                json=crawl_request.dict(exclude_none=True)
            )
            logger.info(f"[CRAWL:{request_id}] Received response: Status Code - {response.status_code}, Body - {response.text}")
            response.raise_for_status()
            json_response = response.json()

            if not json_response.get('results'):
                error_msg = "No results found in crawl response"
                logger.error(f"[CRAWL:{request_id}] {error_msg}")
                raise HTTPException(status_code=404, detail=error_msg)

            # Get metadata and cleaned HTML from the response
            result_data = json_response['results'][0]
            cleaned_html = result_data.get('cleaned_html', '')
            metadata = result_data.get('metadata', {})

            # Log metadata keys for debugging
            logger.debug(f"[CRAWL:{request_id}] Received response with metadata keys: {list(metadata.keys())}")
            if 'title' in metadata:
                logger.debug(f"[CRAWL:{request_id}] Title from metadata: {metadata['title']}")

            # Parse the cleaned HTML
            soup = BeautifulSoup(cleaned_html, 'html.parser')

            # Initialize the result dictionary with default values
            result = {
                'id': '',
                'title': metadata.get('title', 'Not specified'),
                'description': metadata.get('description', 'No description available.'),
                'scope_of_service': 'Not specified',
                'scope_of_work': 'Not specified',
                'posted_date': 'Not specified',
                'expiry_date': 'Not specified',
                'deadline': 'Not specified',
                'question_deadline': 'Not specified',
                'location': 'Not specified',
                'budget': 'Not specified',
                'eligibility': 'Not specified',
                'work_performance': 'Not specified',
                'category': RFPCategory.from_url(url).value.replace('-', ' ').title(),
                'country': 'USA',
                'state': '',
                'url': url
            }

            # Extract RFP ID from URL
            rfp_id_match = re.search(r'/(\d+[-\w-]+)\.html', url) or re.search(r'/([\w-]+)\.html', url)
            if rfp_id_match:
                result['id'] = rfp_id_match.group(1)

            # Extract title
            title_elem = soup.find('h1')
            if title_elem:
                result['title'] = title_elem.get_text(strip=True)

            # Find all text content
            content = soup.get_text('\n', strip=True)

            # Extract posted date
            posted_match = re.search(r'Posted Date\s*:\s*([^\n]+)', content)
            if posted_match:
                result['posted_date'] = posted_match.group(1).strip()

            # Extract expiry date
            expiry_match = re.search(r'Expiry Date\s*:\s*([^\n]+)', content)
            if expiry_match:
                result['expiry_date'] = expiry_match.group(1).strip()

            # Extract question deadline
            question_match = re.search(r'Question Answer Deadline\s*:\s*([^\n]+)', content)
            if question_match:
                result['question_deadline'] = question_match.group(1).strip()

            # Extract budget
            budget_match = re.search(r'\[\*\]\s*Budget:([^\[]+)', content, re.DOTALL)
            if budget_match:
                result['budget'] = budget_match.group(1).strip()

            # Extract scope of service
            scope_match = re.search(r'\[\*\]\s*Scope of Service:([^\[]+)', content, re.DOTALL)
            if scope_match:
                scope_text = scope_match.group(1).strip()
                # Clean up the scope text
                scope_lines = [line.strip() for line in scope_text.split('\n') if line.strip()]
                result['scope_of_service'] = '\n'.join(scope_lines)
                result['scope_of_work'] = result['scope_of_service']

            # Extract eligibility
            eligibility_match = re.search(r'\[\*\]\s*Eligibility:([^\[]+)', content, re.DOTALL)
            if eligibility_match:
                result['eligibility'] = eligibility_match.group(1).strip()

            # Extract work performance
            work_match = re.search(r'\[\*\]\s*Work Performance:([^\[]+)', content, re.DOTALL)
            if work_match:
                result['work_performance'] = work_match.group(1).strip()

            # Extract category
            category_match = re.search(r'Category\s*:\s*([^\n]+)', content)
            if category_match:
                result['category'] = category_match.group(1).strip()

            # Extract country and state
            country_match = re.search(r'Country\s*:\s*([^\n]+)', content)
            if country_match:
                result['country'] = country_match.group(1).strip() or 'USA'

            state_match = re.search(r'State\s*:\s*([^\n]+)', content)
            if state_match:
                result['state'] = state_match.group(1).strip()

            # Extract description from scope if no description found
            if not result.get('description') and 'scope_of_service' in result:
                result['description'] = result['scope_of_service'].split('\n')[0] if result['scope_of_service'] else 'No description available.'

            # Special handling for RFP Mart website
            if 'rfpmart.com' in url:
                # Extract data from JSON-LD if available
                json_ld_data = None
                script_tag = soup.find('script', type='application/ld+json')
                if script_tag and script_tag.string:
                    try:
                        json_ld_data = json.loads(script_tag.string)
                        logger.info(f"[CRAWL:{request_id}] Found JSON-LD data: {json.dumps(json_ld_data, indent=2)[:500]}...")
                    except Exception as e:
                        logger.warning(f"Error parsing JSON-LD data: {str(e)}")

                # Extract basic info
                if json_ld_data and isinstance(json_ld_data, dict):
                    # Extract basic info
                    if 'name' in json_ld_data:
                        result['title'] = json_ld_data.get('name', '').split(' - Deadline ')[0].strip()
                    if 'description' in json_ld_data:
                        result['description'] = json_ld_data.get('description', '')
                    if 'releaseDate' in json_ld_data:
                        result['posted_date'] = json_ld_data.get('releaseDate', '')

                    # Extract offer details
                    if 'offers' in json_ld_data and isinstance(json_ld_data['offers'], dict):
                        offer = json_ld_data['offers']
                        if 'price' in offer and 'priceCurrency' in offer:
                            result['budget'] = f"{offer.get('price', '')} {offer.get('priceCurrency', '')}"
                        if 'priceValidUntil' in offer:
                            result['deadline'] = offer.get('priceValidUntil')
                            result['expiry_date'] = offer.get('priceValidUntil')

                            # Extract SKU as ID if not already set
                            if 'sku' in json_ld_data and not result.get('id'):
                                result['id'] = json_ld_data.get('sku')

            # Process scope text if it was defined in the scope_match block
            if 'scope_text' in locals() and scope_text is not None:
                try:
                    # Initialize section_end
                    section_end = None

                    # Find end marker if it was defined
                    if 'end_marker' in locals() and end_marker is not None:
                        end_pos = scope_text.find(end_marker)
                        if end_pos > 0:
                            section_end = end_pos

                    # If we found an end marker, use it
                    if section_end is not None and section_end > 0:
                        processed_scope = scope_text[:section_end].strip()
                    else:
                        # Otherwise, take first 2000 chars
                        processed_scope = scope_text[:2000].strip()

                    # Clean up the text
                    if processed_scope:
                        result['scope_of_work'] = processed_scope
                        result['scope_of_service'] = processed_scope
                except Exception as e:
                    logger.warning(f"Error processing scope text: {str(e)}")
                    # Fall back to the original scope text if processing fails
                    if scope_text:
                        result['scope_of_work'] = scope_text
                        result['scope_of_service'] = scope_text

            # Also look for traditional tables as a fallback
            if not result.get('scope_of_work') or len(result.get('scope_of_work', '')) < 50:
                # Try specific selectors first
                for selector in ['table.rfp-info', 'table.rfp-details', 'table.details', 'table.info', 'table']:
                    tables = soup.select(selector)
                    if tables:
                        info_tables.extend(tables)
                        break

                # If no tables found with specific selectors, try to find any table that looks like it contains RFP info
                if not info_tables:
                    all_tables = soup.find_all('table')
                    for table in all_tables:
                        # Check if table has at least 2 columns and some rows
                        rows = table.find_all('tr')
                        if len(rows) > 1:
                            for row in rows[:3]:  # Check first 3 rows
                                cells = row.find_all(['td', 'th'])
                                if 1 <= len(cells) <= 3:  # Likely a key-value table
                                    info_tables.append(table)
                                    break

            for table in info_tables:
                for row in table.find_all('tr'):
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True).lower()
                        value = cells[1].get_text(' ', strip=True)

                        # Clean the key and value
                        key = key.lower().strip(' :')
                        value = value.strip()

                        # Skip empty values
                        if not value or value.lower() in ['n/a', 'na', 'tbd', 'tba']:
                            continue

                        # Map the keys to our result fields
                        if any(x in key for x in ['publish', 'post', 'issue', 'announce']):
                            result['posted_date'] = value
                        elif any(x in key for x in ['close', 'deadline', 'due', 'expir', 'submission', 'proposal']):
                            if 'question' in key or 'inquiry' in key or 'clarification' in key:
                                result['question_deadline'] = value
                            else:
                                result['deadline'] = value
                                result['expiry_date'] = value
                        elif 'categor' in key or 'type' in key or 'sector' in key:
                            result['category'] = value
                        elif 'countr' in key:
                            result['country'] = value
                            if not result.get('location'):
                                result['location'] = value
                        elif 'location' in key or 'city' in key or 'region' in key:
                            result['location'] = value
                        elif 'budget' in key or 'fund' in key or 'price' in key or 'cost' in key or 'value' in key:
                            result['budget'] = value
                        elif 'eligib' in key or 'qualif' in key or 'criteria' in key:
                            result['eligibility'] = value
                        elif 'scope' in key or 'work' in key or 'deliver' in key:
                            if not result.get('scope_of_work'):
                                result['scope_of_work'] = value
                                result['scope_of_service'] = value
                        elif 'description' in key or 'summary' in key or 'about' in key:
                            if not result.get('description'):
                                result['description'] = value

            # If we still don't have a title, try to generate one from the URL
            if not result.get('title'):
                title_parts = url.split('/')[-1].split('-rfp.')[0].split('-')
                if title_parts and len(title_parts) > 1:
                    result['title'] = ' '.join(part.capitalize() for part in title_parts[1:])
                else:
                    result['title'] = 'RFP - ' + result['id']
            else:
                # Fallback for other RFP websites
                title_selectors = [
                    'h1.rfp-title', 'h1.entry-title', 'h1.title',
                    'h1.page-title', 'h1.post-title', 'h1',
                    'div.rfp-header h1', 'div.post-header h1'
                ]

                for selector in title_selectors:
                    title_elem = soup.select_one(selector)
                    if title_elem and title_elem.get_text(strip=True):
                        result['title'] = title_elem.get_text(strip=True)
                        break

                # Extract description - try multiple sources
                description_sources = [
                    ('meta[name="description"]', 'content'),
                    ('meta[property="og:description"]', 'content'),
                    ('meta[name="twitter:description"]', 'content'),
                    ('div.rfp-description', None),
                    ('div.entry-content', None),
                    ('div.post-content', None),
                    ('div.content', None),
                    ('div.rfp-details', None)
                ]

                for selector, attr in description_sources:
                    elem = soup.select_one(selector)
                    if elem:
                        if attr:
                            desc = elem.get(attr, '').strip()
                        else:
                            desc = elem.get_text(' ', strip=True)
                        if desc and len(desc) > 10:  # Ensure we're not getting empty or too short descriptions
                            result['description'] = desc
                            break

                # Extract scope of work from common section headers
                scope_headers = [
                    'scope of work', 'scope of services', 'project scope', 'scope',
                    'description of work', 'work description', 'project description'
                ]

                # First try to find a section with these headers
                for header in scope_headers:
                    # Look for headers containing the scope text
                    header_elements = soup.find_all(['h2', 'h3', 'h4', 'h5', 'strong', 'b'],
                                                  string=lambda t: t and header in t.lower())

                    for header_elem in header_elements:
                        scope_content = []
                        # Get the parent container that might hold the content
                        parent = header_elem.find_parent(['div', 'section', 'article', 'main', 'body'])
                        if not parent:
                            continue

                        # Get all elements after the header until the next header
                        current = header_elem.find_next_sibling()
                        while current and current.name not in ['h1', 'h2', 'h3', 'h4', 'h5']:
                            if current.name in ['p', 'div', 'ul', 'ol', 'li']:
                                text = current.get_text(' ', strip=True)
                                if text and len(text) > 10:  # Only add non-empty content
                                    scope_content.append(text)
                            current = current.find_next_sibling()

                        if scope_content:
                            result['scope_of_work'] = '\n\n'.join(scope_content)
                            result['scope_of_service'] = result['scope_of_work']  # Set both for compatibility
                            break

                    if result.get('scope_of_work'):
                        break

                # If no scope found, try to extract from common RFP content patterns
                if not result.get('scope_of_work'):
                    # Look for common RFP content patterns
                    content_containers = soup.select('div.rfp-content, div.rfp-details, div.entry-content, div.post-content')
                    for container in content_containers:
                        paragraphs = container.find_all(['p', 'div'], recursive=False)
                        scope_paragraphs = []
                        for p in paragraphs:
                            text = p.get_text(' ', strip=True)
                            if len(text) > 100:  # Likely contains meaningful content
                                scope_paragraphs.append(text)
                        if scope_paragraphs:
                            result['scope_of_work'] = '\n\n'.join(scope_paragraphs[:3])  # Take first 3 paragraphs max
                            result['scope_of_service'] = result['scope_of_work']
                            break

                # Enhanced details mapping with more variations
                details_map = {
                    # Posted date variations
                    'posted date': 'posted_date',
                    'publish date': 'posted_date',
                    'publication date': 'posted_date',
                    'date posted': 'posted_date',
                    'posted on': 'posted_date',
                    'published on': 'posted_date',
                    'issuance date': 'posted_date',
                    'release date': 'posted_date',
                    'date issued': 'posted_date',

                    # Deadline/Closing date variations
                    'closing date': 'deadline',
                    'deadline': 'deadline',
                    'expiry date': 'deadline',
                    'due date': 'deadline',
                    'submission deadline': 'deadline',
                    'proposal deadline': 'deadline',
                    'bid deadline': 'deadline',
                    'application deadline': 'deadline',
                    'last date': 'deadline',
                    'closes on': 'deadline',
                    'ends on': 'deadline',
                    'expires on': 'deadline',
                    'final date': 'deadline',

                    # Question deadline variations
                    'question deadline': 'question_deadline',
                    'question due date': 'question_deadline',
                    'inquiry deadline': 'question_deadline',
                    'clarification deadline': 'question_deadline',
                    'last date for queries': 'question_deadline',
                    'deadline for questions': 'question_deadline',
                    'inquiry due date': 'question_deadline',
                    'clarification due date': 'question_deadline',

                    # Location variations
                    'location': 'location',
                    'project location': 'location',
                    'work location': 'location',
                    'site location': 'location',
                    'implementation location': 'location',
                    'country': 'country',
                    'state': 'state',
                    'province': 'state',
                    'region': 'state',
                    'county': 'state',
                    'city': 'location',
                    'municipality': 'location',

                    # Budget variations
                    'budget': 'budget',
                    'estimated budget': 'budget',
                    'funding': 'budget',
                    'cost': 'budget',
                    'price': 'budget',
                    'value': 'budget',
                    'estimated cost': 'budget',
                    'estimated value': 'budget',
                    'total budget': 'budget',
                    'project budget': 'budget',
                    'funding amount': 'budget',
                    'maximum budget': 'budget',
                    'not to exceed': 'budget',
                    'nte': 'budget',

                    # Eligibility variations
                    'eligibility': 'eligibility',
                    'eligibility criteria': 'eligibility',
                    'qualifications': 'eligibility',
                    'qualification requirements': 'eligibility',
                    'minimum requirements': 'eligibility',
                    'bidder qualifications': 'eligibility',
                    'vendor qualifications': 'eligibility',
                    'supplier qualifications': 'eligibility',
                    'contractor qualifications': 'eligibility',
                    'selection criteria': 'eligibility',
                    'evaluation criteria': 'eligibility',
                    'minimum qualifications': 'eligibility',
                    'participation requirements': 'eligibility',
                    'bidder requirements': 'eligibility',
                    'vendor requirements': 'eligibility',
                    'supplier requirements': 'eligibility',
                    'contractor requirements': 'eligibility',

                    # Work performance variations
                    'work performance': 'work_performance',
                    'performance requirements': 'work_performance',
                    'deliverables': 'work_performance',
                    'scope of work': 'work_performance',
                    'project deliverables': 'work_performance',
                    'performance standards': 'work_performance',
                    'key performance indicators': 'work_performance',
                    'kpi': 'work_performance',
                    'milestones': 'work_performance',
                    'delivery schedule': 'work_performance',
                    'implementation plan': 'implementation_plan',
                    'project timeline': 'work_performance',
                    'schedule': 'work_performance',
                    'timeline': 'work_performance',
                    'work plan': 'work_performance',
                    'project plan': 'work_performance',
                    'implementation schedule': 'work_performance',
                    'delivery requirements': 'work_performance',
                    'performance metrics': 'work_performance',
                    'quality standards': 'work_performance',

                    # Category/Type variations
                    'category': 'category',
                    'type': 'category',
                    'sector': 'category',
                    'industry': 'category',
                    'classification': 'category',
                    'procurement type': 'category',
                    'bid type': 'category',
                    'tender type': 'category',
                    'solicitation type': 'category',
                    'project type': 'category',
                    'service category': 'category',
                    'product category': 'category',
                    'naics': 'category',
                    'unspsc': 'category',
                    'cpv': 'category',
                    'commodity code': 'category',
                    'goods category': 'category',
                    'services category': 'category'
                }

                # Look for tables with key-value pairs
                for table in soup.find_all('table'):
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all(['th', 'td'])
                        if len(cells) == 2:  # Key-value pair
                            key = cells[0].get_text(strip=True).lower()
                            value = cells[1].get_text(strip=True)

                            # Check if this is a known field
                            for detail_key, field_name in details_map.items():
                                if detail_key in key:
                                    result[field_name] = value
                                    break

                # Look for definition lists
                for dl in soup.find_all('dl'):
                    dt_elements = dl.find_all('dt')
                    for dt in dt_elements:
                        key = dt.get_text(strip=True).lower()
                        dd = dt.find_next_sibling('dd')
                        if dd:
                            value = dd.get_text(strip=True)
                            # Check if this is a known field
                            for detail_key, field_name in details_map.items():
                                if detail_key in key:
                                    result[field_name] = value
                                    break

                # Look for paragraphs with labels (e.g., "Location: New York")
                for p in soup.find_all('p'):
                    text = p.get_text(strip=True).lower()
                    for detail_key, field_name in details_map.items():
                        if ':' in text and detail_key in text:
                            parts = [part.strip() for part in text.split(':', 1)]
                            if len(parts) == 2 and detail_key in parts[0]:
                                result[field_name] = parts[1]
                                break

                # Extract location from title if not found
                if not result.get('location') and result.get('title'):
                    # Look for patterns like "USA (Georgia)" in the title
                    import re
                    location_match = re.search(r'\(([^)]+)\)', result['title'])
                    if location_match:
                        result['location'] = location_match.group(1).strip()
                        # Try to extract country/state
                        if ',' in result['location']:
                            parts = [p.strip() for p in result['location'].split(',')]
                            if len(parts) == 2:
                                result['state'], result['country'] = parts
                        elif result['location'].lower() in ['usa', 'united states', 'us']:
                            result['country'] = 'USA'
                        elif len(result['location'].split()) == 1:  # Single word location
                            if len(result['location']) == 2:  # Likely a state code
                                result['state'] = result['location']
                                result['country'] = 'USA'
                            else:
                                result['country'] = result['location']

                # Create a clean copy of the result for logging (without binary data)
                loggable_result = {
                    'request_id': request_id,
                    'url': url,
                    'status': 'success',
                    'timestamp': datetime.datetime.utcnow().isoformat(),
                    'data': {}
                }

                # Add all fields to the loggable result
                for key, value in result.items():
                    # Skip binary data or very large fields
                    if isinstance(value, (bytes, bytearray)):
                        loggable_result['data'][key] = f'<binary data {len(value)} bytes>'
                    elif key == 'description':
                        # Truncate long descriptions but keep more context
                        desc = str(value)
                        loggable_result['data'][key] = desc[:300] + ('...' if len(desc) > 300 else '')
                        # Still log first 100 chars to info
                        logger.info(f"[CRAWL:{request_id}]   {key}: {desc[:100]}...")
                    else:
                        loggable_result['data'][key] = value
                        logger.info(f"[CRAWL:{request_id}]   {key}: {value}")

                # Check for critical fields
                if not result.get('title') or not result.get('description'):
                    loggable_result['status'] = 'partial_success'
                    loggable_result['warning'] = 'Missing critical fields'
                    logger.warning(f"[CRAWL:{request_id}] Missing critical fields in RFP details")
                else:
                    loggable_result['status'] = 'success'
                    logger.info(f"[CRAWL:{request_id}] Successfully extracted all fields")

                # Log the complete structured data as JSON for telemetry
                try:
                    import json
                    telemetry_log = json.dumps({
                        'type': 'crawl_telemetry',
                        'timestamp': datetime.datetime.utcnow().isoformat(),
                        'request_id': request_id,
                        'url': url,
                        'status': loggable_result['status'],
                        'has_title': bool(result.get('title')),
                        'has_description': bool(result.get('description')),
                        'field_count': len(result),
                        'warning': loggable_result.get('warning')
                    })
                    # Use sys.stderr.write for immediate output in Docker
                    import sys
                    sys.stderr.write(f"[TELEMETRY] {telemetry_log}\n")
                    sys.stderr.flush()
                except Exception as e:
                    logger.error(f"[CRAWL:{request_id}] Failed to log telemetry: {str(e)}")

                return result

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error {e.response.status_code} while fetching {e.request.url}"
        logger.error(f"[CRAWL:{request_id}] {error_msg}")
        # Log telemetry for error case
        try:
            import sys
            telemetry_data = {
                'type': 'crawl_telemetry',
                'timestamp': datetime.datetime.utcnow().isoformat(),
                'request_id': request_id,
                'url': url,
                'status': 'error',
                'error_type': 'http_status_error',
                'status_code': e.response.status_code,
                'message': error_msg
            }
            sys.stderr.write(f"[TELEMETRY] {json.dumps(telemetry_data)}\n")
            sys.stderr.flush()
        except Exception as te:
            logger.error(f"[CRAWL:{request_id}] Failed to log error telemetry: {str(te)}")
        return {"error": error_msg, "request_id": request_id}
    except httpx.RequestError as e:
        error_msg = f"Request error while fetching {url}: {str(e)}"
        logger.error(f"[CRAWL:{request_id}] {error_msg}")
        # Log telemetry for request error case
        try:
            import sys
            telemetry_data = {
                'type': 'crawl_telemetry',
                'timestamp': datetime.datetime.utcnow().isoformat(),
                'request_id': request_id,
                'url': url,
                'status': 'error',
                'error_type': 'request_error',
                'message': str(e)
            }
            sys.stderr.write(f"[TELEMETRY] {json.dumps(telemetry_data)}\n")
            sys.stderr.flush()
        except Exception as te:
            logger.error(f"[CRAWL:{request_id}] Failed to log request error telemetry: {str(te)}")
        return {"error": error_msg, "request_id": request_id}
    except Exception as e:
        error_msg = f"Error in crawl_rfp_details: {str(e)}"
        logger.error(f"[CRAWL:{request_id}] {error_msg}", exc_info=True)
        # Log telemetry for unhandled exception
        try:
            import traceback
            import sys
            telemetry_data = {
                'type': 'crawl_telemetry',
                'timestamp': datetime.datetime.utcnow().isoformat(),
                'request_id': request_id,
                'url': url,
                'status': 'error',
                'error_type': 'unhandled_exception',
                'message': error_msg,
                'exception_type': type(e).__name__,
                'traceback': traceback.format_exc()
            }
            sys.stderr.write(f"[TELEMETRY] {json.dumps(telemetry_data)}\n")
            sys.stderr.flush()
        except Exception as te:
            logger.error(f"[CRAWL:{request_id}] Failed to log exception telemetry: {str(te)}")
        return {"error": error_msg, "request_id": request_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
