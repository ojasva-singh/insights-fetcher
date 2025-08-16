from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict

# Pydantic models define the structure of your API data (requests and responses)

class Product(BaseModel):
    id: int
    title: str
    vendor: str
    product_type: str
    handle: str
    created_at: str
    # This allows other fields from the JSON to be ignored without error
    class Config:
        extra = "ignore"

class FAQItem(BaseModel):
    question: str
    answer: str

class BrandInsights(BaseModel):
    brand_name: Optional[str] = None
    product_catalog: List[Product] = []
    hero_products: List[HttpUrl] = [] # ADDED: Products on the homepage
    policies: Dict[str, str] = {}
    faqs: List[FAQItem] = []
    social_handles: Dict[str, HttpUrl] = {}
    contact_details: Dict[str, List[str]] = {}
    brand_context: Optional[str] = None
    important_links: Dict[str, HttpUrl] = {}
    competitors: List[str] = [] # ADDED: List of competitor domains

class FetchRequest(BaseModel):
    website_url: HttpUrl