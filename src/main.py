import os
import sys
import time
from datetime import datetime
import constants

from apify_client import ApifyClient
from google import genai
from twilio.rest import Client

# Initialize Clients
apify_client = ApifyClient(constants.APIFY_API_TOKEN)
gemini_client = genai.Client(api_key=constants.GEMINI_API_KEY)

# Twilio Check
TWILIO_READY = all([
    getattr(constants, 'TWILIO_ACCOUNT_SID', None),
    getattr(constants, 'TWILIO_AUTH_TOKEN', None)
])

class MasterScout:
    def __init__(self):
        self.primary_query = "Bangalore startup business gaps 2026"
        self.all_raw_data = []

    def log_step(self, platform, items):
        """Prints exact results to the terminal for manual verification."""
        count = len(items)
        print(f"\n--- {platform} Results ---")
        print(f"Items found: {count}")
        if count > 0:
            for i, item in enumerate(items[:3]):
                # Updated logic to handle different platform schemas
                text = item.get('title') or item.get('fullText') or item.get('snippet') or "No text content"
                print(f"  {i+1}. {text[:100]}...")
        else:
            print("  ⚠️ No data found. Check query or actor status.")
        print("-" * 30)

    def scrape_reddit(self):
        print("\nStep 1: Reddit Multi-Timeline Scrape")
        timeframes = ["day", "week", "month"]
        for tf in timeframes:
            try:
                run_input = {
                    "searchTerm": self.primary_query,
                    "maxPosts": 50, 
                    "searchTime": tf,
                    "searchSort": "relevance",
                    "scrapeType": "post"
                }
                run = apify_client.actor("peakydev/reddit-scraper-post-comments-users").call(run_input=run_input)
                items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items(limit=20))
                self.log_step(f"Reddit ({tf})", items)
                
                titles = "\n".join([i.get('title', '') for i in items])
                self.all_raw_data.append(f"[REDDIT {tf.upper()}]: {titles}")
            except Exception as e:
                print(f"❌ Reddit {tf} Error: {e}")

    def scrape_twitter_apidojo(self):
        print("\nStep 2: Twitter Scrape (ApiDojo)")
        try:
            # apidojo/tweet-scraper schema
            run_input = {
                "searchTerms": [self.primary_query],
                "sort": "Latest",
                "maxTweets": 20,
            }
            run = apify_client.actor("apidojo/tweet-scraper").call(run_input=run_input)
            items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items(limit=20))
            self.log_step("Twitter", items)
            
            tweets = "\n".join([i.get('fullText', '') for i in items if i.get('fullText')])
            self.all_raw_data.append(f"[TWITTER]: {tweets}")
        except Exception as e:
            print(f"❌ Twitter Error: {e}")

    def scrape_google_search(self):
        print("\nStep 3: Google Search Scrape (Apify)")
        try:
            # apify/google-search-scraper schema
            run_input = {
                "queries": self.primary_query,
                "maxPagesPerQuery": 1,
                "resultsPerPage": 10,
                "mobileResults": False
            }
            run = apify_client.actor("apify/google-search-scraper").call(run_input=run_input)
            items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items(limit=10))
            
            # Extract organic results from the Google schema
            organic_results = []
            for page in items:
                organic_results.extend(page.get('organicResults', []))
            
            self.log_step("Google Search", organic_results)
            
            snippets = "\n".join([f"{res.get('title')}: {res.get('snippet')}" for res in organic_results])
            self.all_raw_data.append(f"[GOOGLE SEARCH]: {snippets}")
        except Exception as e:
            print(f"❌ Google Search Error: {e}")

    def analyze_report(self):
        print("\nStep 4: Google Grounding & Gemini Analysis")
        context = "\n\n".join(self.all_raw_data)
        
        prompt = f"""
        SOCIAL & SEARCH DATA CONTEXT:
        {context}

        TASK:
        1. Use Google Search to verify these insights against current March 2026 Bangalore news and trends.
        2. Propose 3 specific SMB business ideas tailored for the Bangalore market.
        
        INCLUDE FOR EACH IDEA:
        - 📊 Success Probability (%)
        - 🏗️ Difficulty (1-10)
        - 💰 Capital (Low/Med/High)
        - ⏱️ Time-to-Revenue (Weeks)
        - 🚀 24h Quick Start Step
        
        Format for WhatsApp with bolding and emojis.
        """
        try:
            # Note: Ensure constants.GEMINI_API_KEY supports the model version used
            response = gemini_client.models.generate_content(
                model="gemini-2.0-flash", # Adjusted to current available flash model
                contents=prompt,
                config={'tools': [{'google_search': {}}]}
            )
            return response.text
        except Exception as e:
            return f"Analysis Error: {e}"

def main():
    scout = MasterScout()
    
    scout.scrape_reddit()
    scout.scrape_twitter_apidojo()
    scout.scrape_google_search()
    
    report = scout.analyze_report()
    
    final_output = f"🚀 *Master Scout: Bangalore 2026* 🚀\n\n{report}"
    
    print("\n--- FINAL MASTER REPORT ---")
    print(final_output)

    if TWILIO_READY:
        try:
            client = Client(constants.TWILIO_ACCOUNT_SID, constants.TWILIO_AUTH_TOKEN)
            client.messages.create(
                from_=constants.TWILIO_WHATSAPP_FROM,
                body=final_output,
                to=constants.TWILIO_WHATSAPP_TO
            )
            print("\n✅ WhatsApp Delivered!")
        except Exception as e:
            print(f"\n❌ Twilio delivery failed: {e}")

if __name__ == "__main__":
    main()
