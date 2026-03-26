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
        # Broadened queries to ensure we get more than 1 result
        run_input = {
            "queries": [
                "Bangalore business problems", 
                "Bangalore startup niche", 
                "Bangalore infrastructure issues",
                "Bengaluru service gaps"
            ],
            "maxPosts": 100, # PeakyDev requirement
            "includeComments": False 
        }
        run = apify_client.actor("peakydev/reddit-scraper-post-comments-users").call(run_input=run_input)
        
        items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items())
        
        # LOGGING: Vital for debugging
        count = len(items)
        print(f"DEBUG: Scraper returned {count} items.")
        
        if count == 0:
            return "No specific Reddit trends found today. Use Google Search instead."

        # Truncate to top 15 titles to avoid hitting Gemini's token/rate limits
        data = "\n".join([item.get('title', '') for item in items[:15]])
        return data

    except Exception as e:
        print(f"Reddit Scraping failed: {e}")
        return "Scraping failed, relying entirely on Google Search."

def analyze_and_send():
    print(f"[{datetime.now()}] Starting Hybrid Scout (Gemini 1.5 Flash)...")
    try:
        reddit_data = scrape_reddit()
        
        # We use Gemini 1.5 Flash for better free-tier quota stability
        prompt = f"""
        Reddit Data: {reddit_data}

        Task: Use your built-in Google Search tool to find 2 current (2026) 
        complaints or service gaps in Bangalore. Look for issues like:
        - Traffic/Logistics bottlenecks
        - Water or Power infrastructure
        - Tech-worker burnout/lifestyle needs
        
        Suggest 2 high-potential SMB (Small-Medium Business) ideas.
        Format as a professional yet catchy WhatsApp message with emojis.
        """

        print("Gemini (1.5 Flash) is searching Google and analyzing...")
        response = gemini_client.models.generate_content(
            model="gemini-1.5-flash", # More stable Free Tier quota
            contents=prompt,
            config={'tools': [{'google_search': {}}]}
        )

        if not response.text:
            print("ERROR: Gemini returned empty text.")
            return

        print("Sending WhatsApp via Twilio...")
        twilio_client.messages.create(
            from_=constants.TWILIO_WHATSAPP_FROM,
            body=f"🚀 *Bangalore Business Scout* 🚀\n\n{response.text}",
            to=constants.TWILIO_WHATSAPP_TO
        )
        print("🎉 Success! Check your phone.")

    except Exception as e:
        print(f"CRITICAL FAILURE: {e}")
        # Exit with 0 so Railway doesn't keep retrying and burning your quota
        sys.exit(0) 

if __name__ == "__main__":
    analyze_and_send()
