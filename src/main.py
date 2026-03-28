import os
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
        count = len(items)
        print(f"\n--- {platform} Results ---")
        print(f"Items found: {count}")
        if count > 0:
            for i, item in enumerate(items[:3]):
                text = item.get('title') or item.get('snippet') or item.get('description') or "No text content"
                print(f"  {i+1}. {text[:100]}...")
        print("-" * 30)

    def scrape_reddit(self):
        print("\nStep 1: Reddit Multi-Timeline Scrape")
        for tf in ["day", "week", "month"]:
            try:
                run_input = {
                    "searchTerm": self.primary_query,
                    "maxPosts": 100,  # Actor requires minimum 100
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
                print(f"❌ Reddit Error: {e}")

    def scrape_twitter_via_google(self):
        print("\nStep 2: Twitter Search (via Google)")
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
            print(f"❌ Twitter Workaround Error: {e}")

    def scrape_google_search(self):
        print("\nStep 3: Google Web Scrape")
        try:
            run_input = {
                "queries": self.primary_query,
                "maxPagesPerQuery": 1,
                "resultsPerPage": 10
            }
            run = apify_client.actor("apify/google-search-scraper").call(run_input=run_input)
            items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items())
            organic = []
            for page in items:
                organic.extend(page.get('organicResults', []))
            
            self.log_step("Google Web", organic)
            snippets = "\n".join([f"{res.get('title')}: {res.get('snippet')}" for res in organic])
            self.all_raw_data.append(f"[WEB SEARCH]: {snippets}")
        except Exception as e:
            print(f"❌ Google Search Error: {e}")

    def analyze_report(self):
        print("\nStep 4: Gemini Analysis")
        context = "\n\n".join(self.all_raw_data)
        
        prompt = f"""
        CONTEXT:
        {context}

        TASK:
        1. Identify 3 business gaps in Bangalore for 2026 based on data.
        2. Propose SMB ideas with 24h start steps.
        Format for WhatsApp.
        """
        try:
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt,
                config={'tools': [{'google_search': {}}]}
            )
            return response.text
        except Exception as e:
            return f"Gemini Error: {e}"

def main():
    scout = MasterScout()
    scout.scrape_reddit()
    scout.scrape_twitter_via_google()
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
