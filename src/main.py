import os
import sys
import time  # Added for the buffer
from datetime import datetime
import constants

from apify_client import ApifyClient
from google import genai
from twilio.rest import Client

# Initialize Clients
apify_client = ApifyClient(constants.APIFY_API_TOKEN)
gemini_client = genai.Client(api_key=constants.GEMINI_API_KEY)

# Handle Twilio gracefully
try:
    if hasattr(constants, 'TWILIO_ACCOUNT_SID') and constants.TWILIO_ACCOUNT_SID:
        twilio_client = Client(constants.TWILIO_ACCOUNT_SID, constants.TWILIO_AUTH_TOKEN)
        TWILIO_READY = True
    else:
        TWILIO_READY = False
except Exception:
    TWILIO_READY = False

def scrape_reddit():
    print("Step 1: Scraping Reddit (Past 24 Hours)...")
    try:
        run_input = {
            "queries": ["Bangalore startup gaps", "Bengaluru business problems 2026", "Bangalore community help"],
            "maxPosts": 200, 
            "searchTime": "day",
            "searchSort": "new",
            "includeComments": False
        }
        
        # .call() waits for the actor to finish, but we add a timeout for safety
        print("Waiting for Apify actor to complete...")
        run = apify_client.actor("peakydev/reddit-scraper-post-comments-users").call(
            run_input=run_input,
            wait_for_finish=180 # Wait up to 3 minutes
        )
        
        # A small 2-second buffer to ensure the Apify database is ready for reading
        time.sleep(2)
        
        # Fetch up to 50 items
        dataset_id = run["defaultDatasetId"]
        items = list(apify_client.dataset(dataset_id).iterate_items(limit=50))
        
        print(f"DEBUG: Scraper retrieved {len(items)} fresh items.")
        
        if not items:
            return "No new Reddit trends in the last 24 hours."
            
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
    Reddit Context (Last 24 Hours): 
    {reddit_data}

    Task: 
    1. Cross-reference these fresh Reddit complaints with live 2026 data via Google Search.
    2. Identify 2 high-potential SMB gaps specifically for Bangalore.
    3. Suggest actionable business ideas with a focus on quick execution.
    4. Format for WhatsApp with bold headers and professional emojis.
    """

    print(f"Step 2: Gemini ({model_id}) is searching Google for real-time verification...")
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
    full_message = f"🚀 *Bangalore 24h Business Scout* 🚀\n\n{final_output}"

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
        print("\n📢 TWILIO PENDING: Results printed to terminal:")
        print("-" * 40)
        print(full_message)
        print("-" * 40)

if __name__ == "__main__":
    analyze_and_send()
