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
twilio_client = Client(constants.TWILIO_ACCOUNT_SID, constants.TWILIO_AUTH_TOKEN)

def scrape_reddit():
    print("Step 1: Scraping Reddit...")
    try:
        # We widened the queries significantly to ensure results > 1
        run_input = {
            "queries": ["Bangalore", "Bengaluru", "India startup"],
            "maxPosts": 100,
            "includeComments": False
        }
        run = apify_client.actor("peakydev/reddit-scraper-post-comments-users").call(run_input=run_input)

        items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items())
        count = len(items)
        print(f"DEBUG: Scraper returned {count} items.")

        # Extract titles
        data = "\n".join([item.get('title', '') for item in items[:20]])
        return data if data else "No specific Reddit trends."

    except Exception as e:
        print(f"Reddit Scraping failed: {e}")
        return "Scraping failed, relying on Google Search."

def analyze_and_send():
    print(f"[{datetime.now()}] Starting Hybrid Scout...")
    try:
        reddit_data = scrape_reddit()

        # --- FIX: In the new SDK, use 'gemini-1.5-flash' WITHOUT 'models/' prefix ---
        model_id = "gemini-1.5-flash"

        prompt = f"""
        Reddit Context: {reddit_data}

        Task: Use Google Search to find 2 current (2026) service gaps or
        business problems in Bangalore. Suggest 2 SMB ideas.
        Format for WhatsApp with emojis.
        """

        print(f"Gemini ({model_id}) is searching Google...")
        response = gemini_client.models.generate_content(
            model=model_id,
            contents=prompt,
            config={'tools': [{'google_search': {}}]}
        )

        if not response.text:
            print("ERROR: Empty response from Gemini.")
            return

        print("Sending WhatsApp...")
        twilio_client.messages.create(
            from_=constants.TWILIO_WHATSAPP_FROM,
            body=f"🚀 *Bangalore Business Scout* 🚀\n\n{response.text}",
            to=constants.TWILIO_WHATSAPP_TO
        )
        print("🎉 SUCCESS! Check your phone.")

    except Exception as e:
        # This will catch the 404 if the model name is still wrong
        print(f"CRITICAL FAILURE: {e}")
        sys.exit(0)

if __name__ == "__main__":
    analyze_and_send()
