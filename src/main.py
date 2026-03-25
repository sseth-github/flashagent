import os
import sys
from datetime import datetime
from apify_client import ApifyClient
import google.generativeai as genai
from twilio.rest import Client
# Add the parent directory (root) to the system path so it can find constants.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from constants import *


# Initialize Clients
apify_client = ApifyClient(APIFY_API_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def scrape_data():
    print("Step 1: Scraping Bangalore trends...")
    # Scrape Reddit
    reddit_results = apify_client.actor("trudax/reddit-scraper").call(run_input={
        "searchTerms": ["Bangalore business", "Bangalore startup problems"],
        "maxItems": 10
    })
    
    # Scrape Twitter/X
    twitter_results = apify_client.actor("apidojo/tweet-scraper-lite").call(run_input={
        "searchTerms": ["Bangalore niche business", "Bangalore service gap"],
        "maxItems": 10
    })
    
    data = ""
    for item in apify_client.dataset(reddit_results["defaultDatasetId"]).iterate_items():
        data += f"Reddit: {item.get('title', '')}\n"
    for item in apify_client.dataset(twitter_results["defaultDatasetId"]).iterate_items():
        data += f"Twitter: {item.get('full_text', '')}\n"
    return data

def analyze_and_send():
    print(f"[{datetime.now()}] Starting Daily Scout...")
    try:
        # 1. Get Data
        raw_info = scrape_data()
        
        # 2. Analyze with Gemini
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = f"""
        Analyze these Bangalore social media trends: {raw_info}
        Find the 2 best SMB ideas. Use these parameters:
        - Scalability (1-10)
        - Investment Level (Low/Med)
        - Bangalore 'Why Now' factor (e.g. traffic, water, tech-hubs)
        Format for a clean WhatsApp message with emojis.
        """
        response = model.generate_content(prompt)
        
        # 3. Send WhatsApp
        twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            body=f"🚀 *Bangalore Business Scout* 🚀\n\n{response.text}",
            to=TWILIO_WHATSAPP_TO
        )
        print("Success: Message sent to WhatsApp.")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        sys.exit(1) # Signal failure to Railway logs

if __name__ == "__main__":
    analyze_and_send()
