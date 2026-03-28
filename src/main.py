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
# Set ENABLE_TWILIO_PUSH=True in Railway Variables tab
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
                # Catching variations: title (Reddit), snippet (Google), body (Custom)
                text = item.get('title') or item.get('snippet') or item.get('body') or item.get('description') or "No text content"
                print(f"  {i+1}. {text[:100]}...")
        print("-" * 30)

    def scrape_reddit(self):
        print("\nStep 1: Reddit Multi-Timeline Scrape")
        for tf in ["day", "week", "month"]:
            try:
                run_input
