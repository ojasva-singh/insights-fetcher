import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse

def get_soup(url: str) -> Optional[BeautifulSoup]:
    """Fetches a URL and returns a BeautifulSoup object."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, timeout=15, headers=headers)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching page {url}: {e}")
        return None

def get_product_catalog(base_url: str) -> Optional[List[Dict]]:
    """Fetches the product catalog from the /products.json endpoint."""
    try:
        products_url = f"{base_url.strip('/')}/products.json"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(products_url, timeout=10, headers=headers)
        response.raise_for_status()
        return response.json().get("products", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching product catalog: {e}")
        return None

def get_hero_products(soup: BeautifulSoup, base_url: str) -> List[str]:
    """
    Finds and returns a list of unique product URLs from the homepage by
    identifying product containers using multiple strategies.
    """
    hero_product_urls = set()
    
    # Strategy 1: Common CSS selectors for product containers in Shopify themes
    product_container_selectors = [
        '.grid-product',
        '.product-card', 
        '.product-item',
        '.product-block',
        '.product-tile',
        '.product-grid-item',
        '.featured-product',
        '.collection-item',
        'li.product',
        '[class*="product-item"]',
        '[class*="product-card"]', 
        '[class*="product-grid"]',
        '[class*="product-block"]',
        '[class*="featured-product"]',
        '[data-product-id]',
        '[data-product-handle]'
    ]
    
    # Find all potential product containers
    product_containers = soup.select(', '.join(product_container_selectors))
    print(f"Found {len(product_containers)} potential product containers")
    
    for container in product_containers:
        # Find the first link within the container that points to a product
        product_link = container.find("a", href=re.compile(r'/products/'))
        
        if product_link and product_link.get('href'):
            href = product_link['href']
            
            # Skip collection links that might contain '/products/' in path
            if '/collections/' in href and '/products/' not in href.split('/collections/')[-1]:
                continue
                
            # Skip variant-specific URLs and other non-product paths
            if any(skip_pattern in href for skip_pattern in ['/cart', '/checkout', '/account', '/search']):
                continue
            
            full_url = urljoin(base_url.rstrip('/'), href)
            
            # Clean query parameters and fragments
            cleaned_url = full_url.split('?')[0].split('#')[0]
            
            # Validate that this is actually a product URL
            if is_valid_product_url(cleaned_url):
                hero_product_urls.add(cleaned_url)
    
    # Strategy 2: Look for direct product links in common homepage sections
    homepage_sections = soup.find_all(['section', 'div'], class_=re.compile(r'(featured|hero|collection|products|bestseller)', re.I))
    
    for section in homepage_sections:
        product_links = section.find_all("a", href=re.compile(r'/products/[^/]+/?$'))
        for link in product_links:
            if link.get('href'):
                full_url = urljoin(base_url.rstrip('/'), link['href'])
                cleaned_url = full_url.split('?')[0].split('#')[0]
                if is_valid_product_url(cleaned_url):
                    hero_product_urls.add(cleaned_url)
    
    # Strategy 3: Look for Shopify-specific data attributes
    elements_with_product_data = soup.find_all(attrs={'data-product-id': True})
    elements_with_product_data.extend(soup.find_all(attrs={'data-product-handle': True}))
    
    for element in elements_with_product_data:
        # Find links within these elements
        links = element.find_all('a', href=re.compile(r'/products/'))
        for link in links:
            if link.get('href'):
                full_url = urljoin(base_url.rstrip('/'), link['href'])
                cleaned_url = full_url.split('?')[0].split('#')[0]
                if is_valid_product_url(cleaned_url):
                    hero_product_urls.add(cleaned_url)
    
    # Strategy 4: JSON-LD structured data
    try:
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            if script.string:
                import json
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get('@type') == 'Product':
                        # This is a product page, not homepage - skip
                        continue
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get('@type') == 'Product':
                                product_url = item.get('url')
                                if product_url and '/products/' in product_url:
                                    full_url = urljoin(base_url.rstrip('/'), product_url)
                                    cleaned_url = full_url.split('?')[0].split('#')[0]
                                    if is_valid_product_url(cleaned_url):
                                        hero_product_urls.add(cleaned_url)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Error parsing JSON-LD: {e}")
    
    result = list(hero_product_urls)[:20]  # Limit to top 20 products
    print(f"Found {len(result)} hero products")
    return result

def is_valid_product_url(url: str) -> bool:
    """
    Validates if a URL is a proper Shopify product URL.
    """
    if not url or not isinstance(url, str):
        return False
    
    # Must contain /products/
    if '/products/' not in url:
        return False
    
    # Parse URL to check structure
    try:
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        
        # Should have at least 'products' and a handle
        if len(path_parts) < 2 or path_parts[0] != 'products':
            return False
        
        # Product handle should not be empty and should be reasonable length
        product_handle = path_parts[1]
        if not product_handle or len(product_handle) < 2 or len(product_handle) > 100:
            return False
        
        # Should not contain certain patterns that indicate it's not a product page
        invalid_patterns = [
            'collections', 'pages', 'blogs', 'cart', 'checkout', 
            'account', 'search', 'admin', 'api'
        ]
        
        if any(pattern in url.lower() for pattern in invalid_patterns):
            return False
        
        return True
        
    except Exception:
        return False

def find_links_with_keywords(soup: BeautifulSoup, base_url: str, keywords: List[str]) -> Dict[str, str]:
    """Finds links that contain specific keywords in their text or href."""
    links = {}
    
    # Look in footer first (most reliable location for policy links)
    footer = soup.find('footer')
    nav_elements = soup.find_all(['nav', 'header', 'footer'])
    search_areas = [footer] if footer else []
    search_areas.extend(nav_elements)
    search_areas.append(soup)  # Fallback to entire page
    
    for area in search_areas:
        if not area:
            continue
            
        for a_tag in area.find_all("a", href=True):
            link_text = a_tag.get_text(strip=True).lower()
            href = a_tag['href'].lower()
            
            for keyword in keywords:
                if keyword not in links and (keyword in link_text or keyword in href):
                    full_url = a_tag['href']
                    if full_url.startswith('/'):
                        full_url = f"{base_url.strip('/')}{full_url}"
                    elif not full_url.startswith('http'):
                        continue  # Skip mailto:, tel:, etc.
                    links[keyword] = full_url
                    break
                    
        # Break early if we found all keywords in footer/nav
        if len(links) == len(keywords) and area != soup:
            break
    
    return links

def extract_social_handles(soup: BeautifulSoup) -> Dict[str, str]:
    """Extracts social media links from a page."""
    social_platforms = {
        "instagram": ["instagram.com", "instagr.am"],
        "facebook": ["facebook.com", "fb.com"],
        "twitter": ["twitter.com", "x.com"],
        "tiktok": ["tiktok.com"],
        "youtube": ["youtube.com", "youtu.be"],
        "pinterest": ["pinterest.com"],
        "linkedin": ["linkedin.com"],
        "snapchat": ["snapchat.com"]
    }
    
    handles = {}
    
    # Look in footer and header first
    priority_areas = []
    footer = soup.find('footer')
    header = soup.find('header')
    if footer:
        priority_areas.append(footer)
    if header:
        priority_areas.append(header)
    priority_areas.append(soup)  # Fallback to entire page
    
    for area in priority_areas:
        for a_tag in area.find_all("a", href=True):
            href = a_tag['href'].lower()
            
            for platform, domains in social_platforms.items():
                if platform not in handles:
                    if any(domain in href for domain in domains):
                        handles[platform] = a_tag['href']
                        break
        
        # If we found handles in footer/header, prefer those
        if handles and area != soup:
            break
    
    return handles

def extract_contact_details(soup: BeautifulSoup) -> Dict[str, List[str]]:
    """Extracts email addresses and phone numbers from the page text."""
    
    # Focus on contact-related sections first
    contact_sections = soup.find_all(['section', 'div'], class_=re.compile(r'(contact|footer|about)', re.I))
    contact_pages = soup.find_all('a', href=re.compile(r'(contact|about)', re.I))
    
    # Get text from contact sections and general page
    text_sources = []
    for section in contact_sections:
        text_sources.append(section.get_text())
    
    # Also check the general page text
    text_sources.append(soup.get_text())
    
    all_text = ' '.join(text_sources)
    
    # Improved email regex
    email_pattern = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
    emails = re.findall(email_pattern, all_text)
    
    # Improved phone regex - handles various formats
    phone_patterns = [
        r'(\+\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}',  # US format
        r'\+\d{1,3}[\s.-]?\d{1,4}[\s.-]?\d{1,4}[\s.-]?\d{1,9}',     # International
        r'\b\d{3}[\s.-]?\d{3}[\s.-]?\d{4}\b',                        # Simple US
        r'\b\d{10}\b'                                                # 10 digits
    ]
    
    phones = []
    for pattern in phone_patterns:
        phones.extend(re.findall(pattern, all_text))
    
    # Clean and deduplicate
    emails = list(set([email.lower() for email in emails if '@' in email and '.' in email]))
    phones = list(set([phone.strip() for phone in phones if len(re.sub(r'[^\d]', '', phone)) >= 10]))
    
    return {
        "emails": emails[:5],  # Limit to 5 emails
        "phone_numbers": phones[:3]  # Limit to 3 phone numbers
    }