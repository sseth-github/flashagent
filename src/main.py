import os
import sys
from datetime import datetime
import constants

from apify_client import ApifyClient
from google import genai
from twilio.rest import Client

# Initialize Clients
apify_client = ApifyClient(constants.APIFY_API_TOKEN)

# Verify Gemini Key exists before initializing
if not constants.GEMINI_API_KEY:
    print("CRITICAL: GEMINI_API_KEY is empty. Check Railway Variables.")
    sys.exit(1)

gemini_client = genai.Client(api_key=constants.GEMINI_API_KEY)
twilio_client = Client(constants.TWILIO_ACCOUNT_SID, constants.TWILIO_AUTH_TOKEN)

def scrape_reddit():
    print("Step 1: Scraping Reddit via PeakyDev...")
    try:
        # PeakyDev requires at least 100 maxPosts
        run_input = {
            "queries": ["Bangalore business problems", "Bangalore startup niche"],
            "maxPosts": 100,
            "includeComments": False # Set to False to stay under credit limits
        }
        run = apify_client.actor("peakydev/reddit-scraper-post-comments-users").call(run_input=run_input)

        data = ""
        for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
            data += f"Post: {item.get('title', '')}\n"
        return data if data else "No specific Reddit trends found today."
    except Exception as e:
        print(f"Reddit Scraping failed: {e}")
        return "Scraping failed, relying on Google Search."

def analyze_and_send():
    print(f"[{datetime.now()}] Starting Hybrid Scout...")
    try:
        reddit_data = scrape_reddit()

        prompt = f"""
        Reddit Context: {reddit_data}

        Task: Use Google Search to find current (2026) service gaps in Bangalore.
        Combine with the Reddit info to suggest 2 niche SMB ideas.
        Format for WhatsApp with emojis.
        """

        print("Gemini is searching Google...")
        # Note: 'google_search' is the tool name
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={'tools': [{'google_search': {}}]}
        )

        print("Sending WhatsApp...")
        twilio_client.messages.create(
            from_=constants.TWILIO_WHATSAPP_FROM,
            body=f"🚀 *Bangalore Business Scout* 🚀\n\n{response.text}",
            to=constants.TWILIO_WHATSAPP_TO
        )
        print("Success!")

    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    analyze_and_send()
