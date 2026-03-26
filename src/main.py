import os
import sys
from datetime import datetime
import constants # In the same src/ folder

from apify_client import ApifyClient
from google import genai
from twilio.rest import Client

# Initialize Clients
apify_client = ApifyClient(constants.APIFY_API_TOKEN)
gemini_client = genai.Client(api_key=constants.GEMINI_API_KEY)
twilio_client = Client(constants.TWILIO_ACCOUNT_SID, constants.TWILIO_AUTH_TOKEN)

def scrape_reddit():
    print("Step 1: Scraping Reddit via PeakyDev...")
    try:
        run_input = {
            "queries": ["Bangalore business problems", "Bangalore startup niche"],
            "maxPosts": 100, # PeakyDev minimum
            "includeComments": False 
        }
        run = apify_client.actor("peakydev/reddit-scraper-post-comments-users").call(run_input=run_input)
        
        items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items())
        
        # LOGGING: See exactly what we got back
        count = len(items)
        print(f"DEBUG: Scraper returned {count} items.")
        
        if count == 0:
            return "No specific Reddit trends found today."

        # Collect only titles to save Gemini tokens (prevents 429 errors)
        data = "\n".join([item.get('title', '') for item in items[:20]]) # Top 20 titles only
        return data

    except Exception as e:
        print(f"Reddit Scraping failed: {e}")
        return "Scraping failed, relying on Google Search."

def analyze_and_send():
    print(f"[{datetime.now()}] Starting Hybrid Scout (Flash-Lite)...")
    try:
        reddit_data = scrape_reddit()
        
        # We use Flash-Lite for higher free-tier stability
        prompt = f"""
        Reddit Trends: {reddit_data}

        Task: Using Google Search, find 2 current (2026) service gaps in Bangalore. 
        Focus on infrastructure, tech-lifestyle, or seasonal issues.
        Suggest 2 SMB ideas. Format for WhatsApp with emojis.
        """

        print("Gemini (Flash-Lite) is searching Google...")
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash-lite", # Higher quota model
            contents=prompt,
            config={'tools': [{'google_search': {}}]}
        )

        if not response.text:
            print("ERROR: Gemini returned an empty response.")
            return

        print("Sending WhatsApp...")
        twilio_client.messages.create(
            from_=constants.TWILIO_WHATSAPP_FROM,
            body=f"🚀 *Bangalore Business Scout* 🚀\n\n{response.text}",
            to=constants.TWILIO_WHATSAPP_TO
        )
        print("Success! Message sent.")

    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    analyze_and_send()
