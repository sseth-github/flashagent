import os
import sys
from datetime import datetime
import constants

from apify_client import ApifyClient
from google import genai
from twilio.rest import Client

# Initialize Clients
apify_client = ApifyClient(constants.APIFY_API_TOKEN)
gemini_client = genai.Client(api_key=constants.GEMINI_API_KEY)

# Ensure credentials are not None before initializing Twilio
if not constants.TWILIO_ACCOUNT_SID or not constants.TWILIO_AUTH_TOKEN:
    print("CRITICAL: Twilio credentials missing in constants.py")
    sys.exit(1)

twilio_client = Client(constants.TWILIO_ACCOUNT_SID, constants.TWILIO_AUTH_TOKEN)

def scrape_reddit():
    print("Step 1: Scraping Reddit...")
    try:
        # FIX: maxPosts MUST be >= 100 for this specific actor
        run_input = {
            "queries": ["Bangalore startup gaps", "Bengaluru business problems 2026"],
            "maxPosts": 100, 
            "includeComments": False
        }
        
        run = apify_client.actor("peakydev/reddit-scraper-post-comments-users").call(run_input=run_input)
        dataset_id = run["defaultDatasetId"]
        
        # limit=20 here just controls how many we pull for the prompt
        items = list(apify_client.dataset(dataset_id).iterate_items(limit=20))
        
        print(f"DEBUG: Scraper retrieved {len(items)} items.")
        data = "\n".join([item.get('title', 'No Title') for item in items])
        return data if data else "No specific Reddit trends found."

    except Exception as e:
        print(f"Reddit Scraping failed: {e}")
        return "Scraping failed, relying on Google Search grounding."

def analyze_and_send():
    print(f"[{datetime.now()}] Starting Hybrid Scout...")
    try:
        reddit_data = scrape_reddit()
        model_id = "gemini-2.5-flash"

        prompt = f"""
        Reddit Context (User Complaints/Trends):
        {reddit_data}

        Task: 
        1. Use Google Search to verify if the problems mentioned on Reddit are actual market gaps in Bangalore for 2026.
        2. Identify 2 specific SMB ideas that solve these verified gaps.
        3. Format for WhatsApp with bold text and emojis.
        """

        print(f"Gemini ({model_id}) is grounding with Google Search...")
        
        response = gemini_client.models.generate_content(
            model=model_id,
            contents=prompt,
            config={'tools': [{'google_search': {}}]}
        )

        if not response or not response.text:
            print("ERROR: Gemini returned an empty response.")
            return

        print("Sending WhatsApp via Twilio...")
        # FIX: Ensure sender/receiver include 'whatsapp:' prefix
        twilio_client.messages.create(
            from_=constants.TWILIO_WHATSAPP_FROM, 
            body=f"🚀 *Bangalore Business Scout* 🚀\n\n{response.text}",
            to=constants.TWILIO_WHATSAPP_TO
        )
        print("🎉 SUCCESS! Check your WhatsApp.")

    except Exception as e:
        print(f"CRITICAL FAILURE: {e}")
        sys.exit(1)

if __name__ == "__main__":
    analyze_and_send()
