import os
import sys
import time
from datetime import datetime

# Load constants from constants.py
try:
    import constants
except ImportError:
    print("❌ constants.py not found. Please ensure it is in your root directory.")
    sys.exit(1)

from apify_client import ApifyClient
from google import genai
from twilio.rest import Client

# Initialize Clients
apify_client = ApifyClient(constants.APIFY_API_TOKEN)
gemini_client = genai.Client(api_key=constants.GEMINI_API_KEY)

# Railway Environment Variable Check
PUSH_ENABLED = os.getenv("ENABLE_TWILIO_PUSH", "False").strip().lower() in ("true", "1", "t", "yes")

TWILIO_READY = all([
    getattr(constants, 'TWILIO_ACCOUNT_SID', None),
    getattr(constants, 'TWILIO_AUTH_TOKEN', None),
    getattr(constants, 'TWILIO_WHATSAPP_FROM', None),
    getattr(constants, 'TWILIO_WHATSAPP_TO', None)
])

class MasterScout:
    def __init__(self):
        self.primary_query = "Bangalore startup business gaps 2026"
        self.all_raw_data = []

    def log_step(self, platform, items):
        count = len(items)
        print(f"\n--- {platform} Results ---")
        print(f"Items found: {count}")
        if count > 0:
            for i, item in enumerate(items[:3]):
                text = item.get('title') or item.get('snippet') or item.get('body') or item.get('description') or "No text content"
                print(f"  {i+1}. {text[:100]}...")
        print("-" * 30)

    def scrape_reddit(self):
        print("\nStep 1: Reddit Multi-Timeline Scrape")
        for tf in ["day", "week", "month"]:
            try:
                run_input = {
                    "searchTerm": self.primary_query,
                    "maxPosts": 100,
                    "searchTime": tf,
                    "scrapeType": "post"
                }
                run = apify_client.actor("peakydev/reddit-scraper-post-comments-users").call(run_input=run_input)
                items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items(limit=20))
                self.log_step(f"Reddit ({tf})", items)
                
                titles = "\n".join([i.get('title', i.get('body', '')) for i in items if i.get('title') or i.get('body')])
                if titles:
                    self.all_raw_data.append(f"[REDDIT {tf.upper()}]: {titles}")
            except Exception as e:
                print(f"❌ Reddit Error: {e}")

    def scrape_twitter_via_google(self):
        print("\nStep 2: Twitter Search (via Google Scraper)")
        try:
            run_input = {
                "queries": f"site:x.com {self.primary_query}",
                "maxPagesPerQuery": 1,
                "resultsPerPage": 15
            }
            run = apify_client.actor("apify/google-search-scraper").call(run_input=run_input)
            items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items())
            results = []
            for page in items:
                results.extend(page.get('organicResults', []))
            
            self.log_step("Twitter (via Google)", results)
            tweets = "\n".join([f"{r.get('title')}: {r.get('snippet')}" for r in results])
            self.all_raw_data.append(f"[TWITTER DATA]: {tweets}")
        except Exception as e:
            print(f"❌ Twitter Search Error: {e}")

    def scrape_google_search(self):
        print("\nStep 3: Google Web
