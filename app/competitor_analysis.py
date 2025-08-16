import os
from tavily import TavilyClient
from dotenv import load_dotenv
from urllib.parse import urlparse
import time

# Load environment variables to get the TAVILY_API_KEY
load_dotenv()

# Initialize the Tavily client
try:
    tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
except Exception as e:
    print(f"Error initializing Tavily client: {e}. Competitor search will be skipped.")
    tavily_client = None

def find_competitors(brand_name: str, brand_context: str = "", product_types: list = None) -> list[str]:
    """
    Finds competitors by performing a web search with Tavily and filtering results.
    """
    if not tavily_client:
        print("Tavily client not available, returning empty competitors list")
        return []
    
    if not brand_name:
        print("No brand name provided, returning empty competitors list")
        return []
    
    if product_types is None:
        product_types = []
        
    # Create a focused search query using the top 3 unique and non-empty product types
    product_query = " ".join(list(set(pt for pt in product_types if pt and pt.strip()))[:3])
    
    # Create multiple search queries for better results
    search_queries = []
    
    if product_query:
        search_queries.append(f"direct competitors of {brand_name} {product_query}")
        search_queries.append(f"brands like {brand_name} {product_query}")
        search_queries.append(f"alternatives to {brand_name} {product_query}")
    else:
        # Fallback queries when product types are not available
        search_queries.append(f"direct competitors of {brand_name}")
        search_queries.append(f"brands similar to {brand_name}")
        search_queries.append(f"competitors analysis {brand_name}")
    
    all_competitors = set()
    brand_domain_keywords = [word.lower() for word in brand_name.split() if len(word) > 2]
    
    for query in search_queries:
        print(f"Searching for competitors with query: {query}")
        
        try:
            # Perform the search using the Tavily API
            response = tavily_client.search(
                query=query, 
                search_depth="basic",  # Use basic instead of advanced for faster results
                max_results=8  # Get more results per query
            )
            search_results = response.get('results', [])
            
            # Process results from this search
            competitors_from_query = extract_competitors_from_results(
                search_results, brand_domain_keywords
            )
            all_competitors.update(competitors_from_query)
            
            # Add a small delay to avoid hitting rate limits
            time.sleep(0.5)
            
        except Exception as e:
            print(f"An error occurred during the Tavily API call for query '{query}': {e}")
            continue
    
    # Convert to list and return top 5
    return list(all_competitors)[:5]

def extract_competitors_from_results(search_results: list, brand_domain_keywords: list) -> set:
    """
    Extract competitor domains from search results with improved filtering.
    """
    competitors = set()
    
    excluded_domains = {
        'facebook', 'instagram', 'youtube', 'pinterest', 'twitter', 'x.com',
        'linkedin', 'wikipedia', 'amazon', 'myntra', 'flipkart', 'forbes', 
        'inc.com', 'reddit', 'quora', 'medium', 'techcrunch', 'crunchbase',
        'bloomberg', 'reuters', 'google', 'bing', 'yahoo', 'shopify',
        'squarespace', 'wix', 'wordpress', 'github', 'stackoverflow',
        'aliexpress', 'alibaba', 'ebay', 'etsy', 'tiktok', 'snapchat'
    }
    
    for result in search_results:
        try:
            url = result.get('url')
            title = result.get('title', '').lower()
            content = result.get('content', '').lower()
            
            if not url:
                continue

            # Parse domain
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.replace('www.', '').lower()
            
            # Skip if domain is empty
            if not domain:
                continue
            
            # Filter out the original brand using multiple checks
            brand_found_in_domain = any(keyword in domain for keyword in brand_domain_keywords)
            
            # Filter out excluded domains
            excluded_found = any(excluded in domain for excluded in excluded_domains)
            
            if not brand_found_in_domain and not excluded_found:
                # Additional check: ensure this looks like a legitimate brand website
                if is_legitimate_brand_domain(domain, title, content):
                    # Get root domain to avoid subdomains of the same competitor
                    domain_parts = domain.split('.')
                    if len(domain_parts) >= 2:
                        root_domain = '.'.join(domain_parts[-2:])
                        competitors.add(root_domain)
                        
        except Exception as e:
            print(f"Error processing search result: {e}")
            continue
            
    return competitors

def is_legitimate_brand_domain(domain: str, title: str, content: str) -> bool:
    """
    Check if a domain appears to be a legitimate brand website.
    """
    # Skip if domain has suspicious patterns
    suspicious_patterns = [
        'blog.', 'news.', 'wiki.', 'forum.', 'support.', 'help.',
        'api.', 'dev.', 'docs.', 'cdn.', 'static.', 'img.',
        '.blogspot.', '.wordpress.', '.tumblr.', '.medium.'
    ]
    
    if any(pattern in domain for pattern in suspicious_patterns):
        return False
    
    # Check if it's a proper domain (has at least one dot and proper TLD)
    domain_parts = domain.split('.')
    if len(domain_parts) < 2:
        return False
    
    # Common TLDs for brand websites
    common_tlds = {
        'com', 'co', 'net', 'org', 'in', 'co.in', 'co.uk', 'ca', 
        'au', 'de', 'fr', 'it', 'es', 'br', 'mx', 'jp', 'kr'
    }
    
    tld = '.'.join(domain_parts[-2:]) if len(domain_parts) >= 2 else domain_parts[-1]
    
    # Must have a recognized TLD
    if not any(tld.endswith(common_tld) for common_tld in common_tlds):
        return False
    
    # Additional heuristics based on content
    brand_indicators = [
        'shop', 'store', 'buy', 'collection', 'product', 'brand',
        'fashion', 'clothing', 'apparel', 'accessories', 'jewelry'
    ]
    
    content_lower = (title + ' ' + content).lower()
    has_brand_indicators = any(indicator in content_lower for indicator in brand_indicators)
    
    return has_brand_indicators