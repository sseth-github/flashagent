import os
import sys
from datetime import datetime

# --- FIX: Tell Python to look in the root folder for constants.py ---
# This adds the folder above 'src/' to the search path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from constants import *
except ImportError:
    print("Error: Could not find constants.py. Ensure it is in the root directory.")
    sys.exit(1)

from apify_client import ApifyClient
from google import genai
from twilio.rest import Client

# Initialize Clients using the NEW google-genai SDK
apify_client = ApifyClient(APIFY_API_TOKEN)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def scrape_data():
    print("Step 1: Scraping Bangalore trends...")
    # Scrape Reddit - focusing on local context
    reddit_results = apify_client.actor("trudax/reddit-scraper").call(run_input={
        "searchTerms": ["Bangalore business", "Bangalore startup problems", "niche Bangalore"],
        "maxItems": 10
    })
    
    # Scrape Twitter/X Lite
    twitter_results = apify_client.actor("apidojo/tweet-scraper-lite").call(run_input={
        "searchTerms": ["Bangalore business idea", "Bangalore service gap"],
        "maxItems": 10
    })
    
    data = ""
    for item in apify_client.dataset(reddit_results["defaultDatasetId"]).iterate_items():
        data += f"Reddit: {item.get('title', '')} - {item.get('selftext', '')[:200]}\n"
    for item in apify_client.dataset(twitter_results["defaultDatasetId"]).iterate_items():
        data += f"Twitter: {item.get('full_text', '')}\n"
    return data

def analyze_and_send():
    print(f"[{datetime.now()}] Starting Daily Scout...")
    try:
        raw_info = scrape_data()
        
        # Using the new SDK syntax for Gemini 2.0 Flash
        prompt = f"""
        Analyze these Bangalore social media trends: {raw_info}
        
        Find the 2 best Small-to-Medium Business (SMB) ideas for Bangalore.
        Evaluate based on:
        - Scalability (1-10)
        - Investment Level (Low/Med)
        - Bangalore 'Why Now' factor (e.g. traffic, water, shifting demographics)
        
        Format as a clean, catchy WhatsApp message with emojis.
        """
        
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        # Send via Twilio
        twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            body=f"🚀 *Bangalore Business Scout* 🚀\n\n{response.text}",
            to=TWILIO_WHATSAPP_TO
        )
        print("Success: Message sent to WhatsApp.")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    analyze_and_send()
