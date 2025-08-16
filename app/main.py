from fastapi import FastAPI, HTTPException
from . import models, scraper, ai_processor, competitor_analysis

app = FastAPI(
    title="Shopify Store Insights-Fetcher",
    description="An API to fetch and structure data from Shopify websites."
)

@app.post("/fetch-insights", response_model=models.BrandInsights)
async def fetch_insights(request: models.FetchRequest):
    base_url = str(request.website_url)
    
    try:
        # 1. Get the homepage soup
        homepage_soup = scraper.get_soup(base_url)
        if not homepage_soup:
            raise HTTPException(status_code=404, detail="Website not found or could not be accessed.")

        # 2. Scrape core information
        product_catalog = scraper.get_product_catalog(base_url) or []
        
        # 2.1. Get hero products from homepage
        hero_products = scraper.get_hero_products(homepage_soup, base_url)
        
        link_keywords = ["privacy", "refund", "return", "contact", "faq", "about", "track"]
        important_links = scraper.find_links_with_keywords(homepage_soup, base_url, link_keywords)
        social_handles = scraper.extract_social_handles(homepage_soup)
        contact_details = scraper.extract_contact_details(homepage_soup)

        # 3. Process linked pages using Gemini for structured data
        brand_context, faqs, policies = "", [], {}

        if 'about' in important_links:
            about_soup = scraper.get_soup(important_links['about'])
            if about_soup:
                about_text = about_soup.get_text(separator=' ', strip=True)
                # Ask Gemini for a simple summary
                brand_context_data = ai_processor.get_structured_data_from_text(
                    about_text, "{'summary': 'A concise, one-paragraph summary of the brand.'}"
                )
                brand_context = brand_context_data.get('summary', about_text[:500])

        if 'faq' in important_links:
            faq_soup = scraper.get_soup(important_links['faq'])
            if faq_soup:
                faq_text = faq_soup.get_text(separator=' ', strip=True)
                faq_data = ai_processor.get_structured_data_from_text(
                    faq_text, "{'faqs': [{'question': 'string', 'answer': 'string'}]}"
                )
                faqs = faq_data.get('faqs', [])

        for policy_key in ['privacy', 'refund', 'return']:
            if policy_key in important_links:
                policy_soup = scraper.get_soup(important_links[policy_key])
                if policy_soup:
                    # Store the full text of the policy
                    policies[f"{policy_key}_policy"] = policy_soup.get_text(strip=True)

        # 4. Extract brand name and get competitors
        brand_name = ""
        if homepage_soup.title and homepage_soup.title.string:
            brand_name = homepage_soup.title.string.split('|')[0].strip()
        
        # Get product types for competitor analysis
        product_types = []
        if product_catalog:
            product_types = [product.get('product_type', '') for product in product_catalog[:10]]
            product_types = [pt for pt in product_types if pt]  # Remove empty strings
        
        # Find competitors
        competitors = competitor_analysis.find_competitors(brand_name, product_types)

        # 5. Assemble the final object
        insights = models.BrandInsights(
            brand_name=brand_name,
            product_catalog=product_catalog,
            hero_products=hero_products,
            policies=policies,
            faqs=faqs,
            social_handles=social_handles,
            contact_details=contact_details,
            brand_context=brand_context,
            important_links=important_links,
            competitors=competitors
        )
        
        return insights

    except Exception as e:
        print(f"An internal error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Shopify Insights Fetcher API. Go to /docs to use the API."}