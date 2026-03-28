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
        # We use single primary terms to avoid multi-query schema errors
        self.primary_query = "Bangalore startup business gaps 2026"
        self.all_raw_data = []

    def log_step(self, platform, items):
        """Prints exact results to the terminal for manual verification."""
        count = len(items)
        print(f"\n--- {platform} Results ---")
        print(f"Items found: {count}")
        if count > 0:
            for i, item in enumerate(items[:3]):
                # Dynamically find text content based on platform schema
                text = item.get('title') or item.get('full_text') or item.get('caption') or "No text content"
                print(f"  {i+1}. {text[:100]}...")
        else:
            print("  ⚠️ No data found. Check query or actor status.")
        print("-" * 30)

    def scrape_reddit(self):
        print("\nStep 1: Reddit Multi-Timeline Scrape")
        timeframes = ["day", "week", "month"]
        for tf in timeframes:
            try:
                # SCHEMA FIX: Use 'searchTerm' (string)
                run_input = {
                    "searchTerm": self.primary_query,
                    "maxPosts": 100, 
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

    def scrape_twitter_iron(self):
        print("\nStep 2: Twitter Scrape (IronCrawler)")
        try:
            # SCHEMA FIX: Use 'query' (string)
            run_input = {
                "query": "Bangalore 2026 startup gaps",
                "section": "latest",
                "maxPages": 1
            }
            run = apify_client.actor("iron-crawler/twitter-search").call(run_input=run_input)
            items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items(limit=20))
            self.log_step("Twitter", items)
            
            tweets = "\n".join([i.get('full_text', i.get('text', '')) for i in items])
            self.all_raw_data.append(f"[TWITTER]: {tweets}")
        except Exception as e:
            print(f"❌ Twitter Error: {e}")

    def scrape_instagram(self):
        print("\nStep 3: Instagram Scrape (ScrapeSmith)")
        try:
            # SCHEMA FIX: Use 'hashtags' (array of strings)
            run_input = {
                "hashtags": ["bangalorebusiness", "bengaluru2026"],
                "resultsLimit": 10
            }
            run = apify_client.actor("scrapesmith/instagram-free-post-scraper").call(run_input=run_input)
            items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items(limit=10))
            self.log_step("Instagram", items)
            
            captions = "\n".join([i.get('caption', '') for i in items if i.get('caption')])
            self.all_raw_data.append(f"[INSTAGRAM]: {captions}")
        except Exception as e:
            print(f"❌ Instagram Error: {e}")

    def analyze_report(self):
        print("\nStep 4: Google Grounding & Gemini 2.5 Analysis")
        context = "\n\n".join(self.all_raw_data)
        
        prompt = f"""
        SOCIAL DATA CONTEXT:
        {context}

        TASK:
        1. Use Google Search to verify these platform insights against current March 2026 Bangalore news.
        2. Propose 3 specific SMB business ideas.
        
        INCLUDE FOR EACH IDEA:
        - 📊 Success Probability (%)
        - 🏗️ Difficulty (1-10)
        - 💰 Capital (Low/Med/High)
        - ⏱️ Time-to-Revenue (Weeks)
        - 🚀 24h Quick Start Step
        
        Format for WhatsApp with bolding and emojis.
        """
        try:
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={'tools': [{'google_search': {}}]}
            )
            return response.text
        except Exception as e:
            return f"Analysis Error: {e}"

def main():
    scout = MasterScout()
    
    scout.scrape_reddit()
    scout.scrape_twitter_iron()
    scout.scrape_instagram()
    
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
