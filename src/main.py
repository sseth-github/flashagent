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

class ScoutEngine:
    def __init__(self):
        self.queries = ["Bangalore startup gaps", "Bengaluru business problems 2026", "Bangalore power cuts"]
        self.combined_context = []

    def scrape_reddit_multi(self):
        # Timeframes requested: 24h, 1 week, 1 month
        timeframes = ["day", "week", "month"]
        print(f"--- Step 1: Multi-Timeline Reddit Scrape ({len(timeframes)} runs) ---")
        
        for tf in timeframes:
            try:
                print(f"Scraping Reddit [{tf}]...")
                run_input = {
                    "queries": self.queries,
                    "maxPosts": 100, 
                    "searchTime": tf,
                    "searchSort": "new" if tf == "day" else "relevance"
                }
                run = apify_client.actor("peakydev/reddit-scraper-post-comments-users").call(run_input=run_input)
                items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items(limit=30))
                titles = [item.get('title', '') for item in items]
                self.combined_context.append(f"--- REDDIT DATA ({tf}) ---\n" + "\n".join(titles))
            except Exception as e:
                print(f"Reddit [{tf}] failed: {e}")

    def scrape_twitter_free(self):
        print("--- Step 2: Scraping Twitter (coder_luffy/free-tweet-scraper) ---")
        try:
            run_input = {"search_queries": self.queries, "max_tweets": 50}
            run = apify_client.actor("coder_luffy/free-tweet-scraper").call(run_input=run_input)
            items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items(limit=30))
            tweets = [item.get('full_text', '') for item in items]
            self.combined_context.append("--- TWITTER DATA ---\n" + "\n".join(tweets))
        except Exception as e:
            print(f"Twitter scrape failed: {e}")

    def scrape_instagram_free(self):
        print("--- Step 3: Scraping Instagram (scrapesmith/instagram-free-post-scraper) ---")
        try:
            # Instagram often works better with single hashtags for these free actors
            run_input = {"hashtags": ["bangalorebusiness", "bengaluruinteriors"], "resultsLimit": 20}
            run = apify_client.actor("scrapesmith/instagram-free-post-scraper").call(run_input=run_input)
            items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items())
            captions = [item.get('caption', '') for item in items]
            self.combined_context.append("--- INSTAGRAM DATA ---\n" + "\n".join(captions))
        except Exception as e:
            print(f"Instagram scrape failed: {e}")

    def analyze_with_factors(self):
        full_context = "\n\n".join(self.combined_context)
        print(f"--- Final Step: Analyzing with Gemini 2.5 ({len(full_context)} chars) ---")
        
        prompt = f"""
        Platform Data Context:
        {full_context}

        Task: Analyze the gaps across Reddit, Twitter, and Instagram for Bangalore in 2026.
        Provide 3 detailed SMB ideas. For each idea, include:
        1. 💡 Idea Name & Concept
        2. 📊 Success Probability Percentage (based on sentiment volume)
        3. 🏗️ Implementation Difficulty (1-10)
        4. 💰 Capital Requirement (Low/Medium/High)
        5. ⏱️ Time-to-Revenue (Weeks)
        6. 🚀 Quick-Start Execution Step
        
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
            return f"Analysis failed: {e}"

def run_scout():
    scout = ScoutEngine()
    scout.scrape_reddit_multi()
    scout.scrape_twitter_free()
    scout.scrape_instagram_free()
    
    result = scout.analyze_with_factors()
    
    print("\n" + "="*50)
    print("🚀 HYBRID SCOUT MASTER REPORT 🚀")
    print("="*50 + "\n")
    print(result)

if __name__ == "__main__":
    run_scout()
