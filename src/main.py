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
        # Broadening queries for better hit rates across platforms
        self.queries = ["Bangalore startup gaps", "Bengaluru business problems 2026", "Bangalore infrastructure issues"]
        self.all_raw_data = []

    def log_platform_results(self, platform, items):
        """Helper to print exactly what we found before moving on."""
        count = len(items)
        print(f"\n{'='*10} {platform.upper()} DATA {'='*10}")
        print(f"Total Results: {count}")
        
        if count > 0:
            for idx, item in enumerate(items[:5]): # Show first 5 as a sample
                text = item.get('title') or item.get('full_text') or item.get('text') or item.get('caption', 'No Text')
                print(f"{idx+1}. {text[:100]}...")
        else:
            print("⚠️ No data found for this platform/timeframe.")
        print(f"{'='*30}\n")

    def scrape_reddit(self):
        print("--- Step 1: Reddit Multi-Timeline Scrape ---")
        timeframes = ["day", "week", "month"]
        for tf in timeframes:
            try:
                run_input = {
                    "queries": self.queries,
                    "maxPosts": 50, 
                    "searchTime": tf,
                    "searchSort": "relevance"
                }
                run = apify_client.actor("peakydev/reddit-scraper-post-comments-users").call(run_input=run_input)
                items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items(limit=20))
                
                self.log_platform_results(f"Reddit ({tf})", items)
                
                titles = "\n".join([i.get('title', '') for i in items])
                self.all_raw_data.append(f"[REDDIT {tf.upper()}]:\n{titles}")
            except Exception as e:
                print(f"❌ Reddit {tf} Error: {e}")

    def scrape_twitter_iron(self):
        print("--- Step 2: Twitter Scrape (IronCrawler) ---")
        try:
            # Using iron-crawler/twitter-search
            run_input = {
                "searchTerms": ["Bangalore gaps", "Bengaluru 2026 business"],
                "maxTweets": 20
            }
            run = apify_client.actor("iron-crawler/twitter-search").call(run_input=run_input)
            items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items(limit=20))
            
            self.log_platform_results("Twitter (Iron)", items)
            
            tweets = "\n".join([i.get('full_text', i.get('text', '')) for i in items])
            self.all_raw_data.append(f"[TWITTER]:\n{tweets}")
        except Exception as e:
            print(f"❌ Twitter Error: {e}")

    def scrape_instagram_free(self):
        print("--- Step 3: Instagram Scrape (ScrapeSmith) ---")
        try:
            run_input = {"hashtags": ["bangalorebusiness", "bengaluru2026"], "resultsLimit": 10}
            run = apify_client.actor("scrapesmith/instagram-free-post-scraper").call(run_input=run_input)
            items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items(limit=10))
            
            self.log_platform_results("Instagram", items)
            
            captions = "\n".join([i.get('caption', '') for i in items if i.get('caption')])
            self.all_raw_data.append(f"[INSTAGRAM]:\n{captions}")
        except Exception as e:
            print(f"❌ Instagram Error: {e}")

    def analyze_and_ground(self):
        print("\n--- Step 4: Google Grounding & Gemini Analysis ---")
        full_context = "\n\n".join(self.all_raw_data)
        
        prompt = f"""
        SOCIAL MEDIA CONTEXT (Reddit 24h/1w/1m, Twitter, Instagram):
        {full_context}

        TASK:
        1. Use Google Search to verify these gaps against March 2026 news and data for Bangalore.
        2. Propose 3 SMB ideas. For each, include:
           - 📊 Success Probability (%)
           - 🏗️ Difficulty (1-10)
           - 💰 Capital (Low/Med/High)
           - ⏱️ Time-to-Revenue (Weeks)
           - 🚀 24h Quick Start Action
        
        Format for WhatsApp with bold headers and emojis.
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
    
    # Run Scrapers
    scout.scrape_reddit()
    scout.scrape_twitter_iron()
    scout.scrape_instagram_free()
    
    # Run AI Analysis
    report = scout.analyze_and_ground()
    
    # Final Output Delivery
    final_report = f"🌟 *BANGALORE HYBRID SCOUT REPORT* 🌟\n\n{report}"
    
    print("\n" + "="*40)
    print("FINAL REPORT PREVIEW")
    print("="*40)
    print(final_report)

    if TWILIO_READY:
        try:
            client = Client(constants.TWILIO_ACCOUNT_SID, constants.TWILIO_AUTH_TOKEN)
            client.messages.create(
                from_=constants.TWILIO_WHATSAPP_FROM,
                body=final_report,
                to=constants.TWILIO_WHATSAPP_TO
            )
            print("\n✅ Sent to WhatsApp successfully!")
        except Exception as e:
            print(f"\n❌ Twilio delivery failed: {e}")
    else:
        print("\n📢 Twilio keys missing. Result displayed in terminal only.")

if __name__ == "__main__":
    main()
