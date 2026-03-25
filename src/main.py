import os
import asyncio
from datetime import datetime
from apify_client import ApifyClient
import google.generativeai as genai
from twilio.rest import Client
from apscheduler.schedulers.blocking import BlockingScheduler
from constants import *

# Initialize Clients
apify_client = ApifyClient(APIFY_API_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def scrape_data():
    """Scrapes Reddit and Twitter for Bangalore business trends."""
    # Using 'trudax/reddit-scraper' for Reddit
    reddit_results = apify_client.actor("trudax/reddit-scraper").call(run_input={
        "searchTerms": ["Bangalore business", "Bangalore startup", "Bangalore niche"],
        "maxItems": 15
    })
    
    # Using 'apidojo/tweet-scraper' for X/Twitter
    twitter_results = apify_client.actor("apidojo/tweet-scraper").call(run_input={
        "searchTerms": ["Bangalore business ideas", "Bangalore problem"],
        "maxItems": 15
    })
    
    data = ""
    for item in apify_client.dataset(reddit_results["defaultDatasetId"]).iterate_items():
        data += f"Reddit: {item.get('title', '')} {item.get('selftext', '')}\n"
    for item in apify_client.dataset(twitter_results["defaultDatasetId"]).iterate_items():
        data += f"Twitter: {item.get('full_text', '')}\n"
    return data

def analyze_with_gemini(raw_data):
    """Uses Gemini 2.0 Flash to find the best business idea."""
    model = genai.GenerativeModel('gemini-2.0-flash')
    prompt = f"""
    Based on this raw data from Bangalore social media:
    {raw_data}

    Identify the top 2 Small-to-Medium business ideas for Bangalore.
    For each idea, provide:
    1. Name & Concept
    2. Target Audience in Bangalore
    3. Scalability (1-10)
    4. Estimated Initial Investment (Low/Med/High)
    5. 'Why now?' Factor (Market gap)
    6. Local competitive advantage
    """
    response = model.generate_content(prompt)
    return response.text

def send_whatsapp(message):
    """Pings results via Twilio WhatsApp."""
    twilio_client.messages.create(
        from_=TWILIO_WHATSAPP_FROM,
        body=f"🚀 *Daily Bangalore Business Scout* 🚀\n\n{message}",
        to=TWILIO_WHATSAPP_TO
    )

def daily_job():
    print(f"[{datetime.now()}] Starting daily scout...")
    try:
        raw_info = scrape_data()
        business_ideas = analyze_with_gemini(raw_info)
        send_whatsapp(business_ideas)
        print("Success: Daily digest sent.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone=TIMEZONE)
    # Schedule for 8:00 AM daily in Bangalore
    hour, minute = DAILY_RUN_TIME.split(':')
    scheduler.add_job(daily_job, 'cron', hour=hour, minute=minute)
    
    print(f"Agent online. Scheduled for {DAILY_RUN_TIME} {TIMEZONE} daily.")
    scheduler.start()
