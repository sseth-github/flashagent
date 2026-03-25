import os
import sys
from datetime import datetime

# Now that constants.py is in the same folder (src/), import it directly
try:
    import constants
except ImportError:
    print("Error: constants.py not found in src/ folder.")
    sys.exit(1)

from apify_client import ApifyClient
from google import genai
from twilio.rest import Client

# Initialize Clients using variables from the imported constants module
# Note: Ensure these names match exactly what is in your constants.py
apify_client = ApifyClient(constants.APIFY_API_TOKEN)
gemini_client = genai.Client(api_key=constants.GEMINI_API_KEY)
twilio_client = Client(constants.TWILIO_ACCOUNT_SID, constants.TWILIO_AUTH_TOKEN)

def scrape_data():
    print("Step 1: Scraping Bangalore-specific trends...")
    
    # Scrape Reddit (r/bangalore, r/india, r/businessideas)
    reddit_results = apify_client.actor("trudax/reddit-scraper").call(run_input={
        "searchTerms": ["Bangalore business", "Bangalore startup problems", "niche Bangalore"],
        "maxItems": 10
    })
    
    # Scrape Twitter/X (Search for local gaps)
    twitter_results = apify_client.actor("apidojo/tweet-scraper-lite").call(run_input={
        "searchTerms": ["Bangalore service gap", "Bangalore business idea"],
        "maxItems": 10
    })
    
    combined_raw_text = ""
    
    print("Extracting Reddit data...")
    for item in apify_client.dataset(reddit_results["defaultDatasetId"]).iterate_items():
        combined_raw_text += f"SOURCE: Reddit | TITLE: {item.get('title', '')} | CONTENT: {item.get('selftext', '')[:300]}\n\n"
        
    print("Extracting Twitter data...")
    for item in apify_client.dataset(twitter_results["defaultDatasetId"]).iterate_items():
        combined_raw_text += f"SOURCE: Twitter | CONTENT: {item.get('full_text', '')}\n\n"
        
    return combined_raw_text

def analyze_and_send():
    print(f"[{datetime.now()}] Starting Daily Scout Analysis...")
    try:
        # 1. Fetch raw data from Apify
        raw_info = scrape_data()
        
        if not raw_info.strip():
            print("No data found from scrapers.")
            return

        # 2. Analyze with Gemini 2.0 Flash (New SDK Syntax)
        prompt = f"""
        System: You are a professional business scout specializing in the Bangalore (Bengaluru) market.
        
        Data: {raw_info}
        
        Task: Based on the provided social media data, find the 2 best Small-to-Medium Business (SMB) ideas specifically for Bangalore.
        
        Evaluate each idea on:
        - Scalability (1-10)
        - Initial Investment (Low/Medium)
        - The 'Bangalore Edge': Why this works here specifically (e.g., solving traffic, targeting tech-workers, water issues, or local hobbies).
        
        Format: Create a clean, punchy WhatsApp message using emojis. Keep it readable.
        """
        
        print("Generating business ideas with Gemini...")
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        # 3. Send via Twilio WhatsApp
        print("Sending WhatsApp message...")
        twilio_client.messages.create(
            from_=constants.TWILIO_WHATSAPP_FROM,
            body=f"🚀 *Daily Bangalore Business Scout* 🚀\n\n{response.text}",
            to=constants.TWILIO_WHATSAPP_TO
        )
        print("Success! Check your WhatsApp.")
        
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    analyze_and_send()
