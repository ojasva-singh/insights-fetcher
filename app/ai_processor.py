import os
import google.generativeai as genai
from dotenv import load_dotenv
import json

load_dotenv()

# Configure the Gemini API
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
except Exception as e:
    print(f"Error configuring Gemini: {e}")
    model = None

def get_structured_data_from_text(text_content: str, data_schema: str) -> dict:
    """Uses Gemini to extract structured data from raw text."""
    if not model:
        return {"error": "Gemini model not initialized."}
    if not text_content:
        return {"error": "No text content provided."}

    prompt = f"""
    Analyze the following text from a company's website.
    Extract the information based on the requested JSON schema.
    Return ONLY a valid JSON object. Do not include markdown formatting or any text outside the JSON.

    REQUESTED SCHEMA:
    {data_schema}

    TEXT CONTENT (first 12000 characters):
    ---
    {text_content[:12000]}
    ---
    """
    try:
        response = model.generate_content(prompt)
        # Clean up potential markdown formatting from the response
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_response)
    except Exception as e:
        print(f"Error processing with Gemini or parsing JSON: {e}")
        return {"error": "Failed to get structured data from AI."}