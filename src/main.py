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

# Handle Twilio gracefully while setup is pending
try:
    if hasattr(constants, 'TWILIO_ACCOUNT_SID') and constants.TWILIO_ACCOUNT_SID:
        twilio_client = Client(constants.TWILIO_ACCOUNT_SID, constants.TWILIO_AUTH_TOKEN)
        TWILIO_READY = True
    else:
        TWILIO_READY = False
except Exception:
    TWILIO_READY = False

def scrape_reddit():
    print("Step 1: Scraping Reddit...")
    try:
        # FIX: maxPosts must be >= 100 for this actor
        run_input = {
            "queries": ["Bangalore startup gaps", "Bengaluru business problems 2026"],
            "maxPosts": 100, 
            "includeComments": False
        }
        
        run = apify_client.actor("peakydev/reddit-scraper-post-comments-users").call(run_input=run_input)
        items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items(limit=20))
        
        print(f"DEBUG: Scraper retrieved {len(items)} items.")
        return "\n".join([item.get('title', 'No Title') for item in items])

    except Exception as e:
        print(f"⚠️ Reddit Scraping failed: {e}")
        return "Scraping failed, relying on Google Search grounding."

def analyze_and_send():
    print(f"[{datetime.now()}] Starting Hybrid Scout...")
    
    # 1. Get Data
    reddit_data = scrape_reddit()

    # 2. Process with Gemini 2.5
    model_id = "gemini-2.5-flash"
    prompt = f"""
    Reddit Context: {reddit_data}
    Task: 
    1. Use Google Search to verify current 2026 market gaps in Bangalore.
    2. Suggest 2 specific SMB ideas.
    3. Format for WhatsApp with bold text and emojis.
    """

    print(f"Step 2: Gemini ({model_id}) is searching Google...")
    try:
        response = gemini_client.models.generate_content(
            model=model_id,
            contents=prompt,
            config={'tools': [{'google_search': {}}]}
        )
        
        final_output = response.text if response.text else "Failed to generate insights."
    except Exception as e:
        print(f"CRITICAL FAILURE in Gemini: {e}")
        return

    # 3. Deliver Result
    full_message = f"🚀 *Bangalore Business Scout* 🚀\n\n{final_output}"

    if TWILIO_READY:
        print("Step 3: Sending WhatsApp...")
        try:
            twilio_client.messages.create(
                from_=constants.TWILIO_WHATSAPP_FROM, 
                body=full_message,
                to=constants.TWILIO_WHATSAPP_TO
            )
            print("🎉 SUCCESS! Check your WhatsApp.")
        except Exception as e:
            print(f"❌ Twilio delivery failed: {e}")
            print(f"\n--- FALLBACK (Terminal Output) ---\n{full_message}")
    else:
        print("\n📢 TWILIO PENDING: Displaying result in terminal instead:")
        print("-" * 40)
        print(full_message)
        print("-" * 40)

if __name__ == "__main__":
    analyze_and_send()
