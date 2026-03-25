import os
import sys
from datetime import datetime
import constants # Now in the same src/ folder

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
        # Using the specific actor you requested
        run_input = {
            "queries": ["Bangalore business problems", "Bangalore startup niche"],
            "maxPosts": 5,
            "includeComments": True
        }
        run = apify_client.actor("peakydev/reddit-scraper-post-comments-users").call(run_input=run_input)
        
        data = ""
        for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
            data += f"Reddit Post: {item.get('title', '')} | Comments: {str(item.get('comments', []))[:500]}\n"
        return data
    except Exception as e:
        print(f"Reddit Scraping failed: {e}")
        return "No Reddit data found."

def analyze_and_send():
    print(f"[{datetime.now()}] Starting Hybrid Scout (Reddit + Google Search)...")
    try:
        # 1. Get raw data from your new Reddit Actor
        reddit_data = scrape_reddit()
        
        # 2. Use Gemini with GOOGLE SEARCH enabled
        # This fills in the gaps from X/Twitter without needing a paid actor
        prompt = f"""
        I have some Reddit data from Bangalore: {reddit_data}
        
        Using your built-in Google Search tool, find the latest (March 2026) 
        business complaints or service gaps mentioned on Twitter/X or 
        Bangalore local news regarding infrastructure, tech-life, or lifestyle.
        
        Based on both sources, suggest 2 high-potential SMB ideas for Bangalore.
        Evaluate on: Scalability, Low/Med Investment, and 'Why Bangalore?'.
        
        Format as a punchy WhatsApp message with emojis.
        """
        
        print("Gemini is searching Google and analyzing Reddit...")
        # Note: The 'google_search' tool is passed in the config
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={
                'tools': [{'google_search': {}}]
            }
        )
        
        # 3. Send via Twilio
        twilio_client.messages.create(
            from_=constants.TWILIO_WHATSAPP_FROM,
            body=f"🚀 *Bangalore Business Scout* 🚀\n\n{response.text}",
            to=constants.TWILIO_WHATSAPP_TO
        )
        print("Success! Check your WhatsApp.")
        
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    analyze_and_send()
