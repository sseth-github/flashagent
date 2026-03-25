"""
Loads environment/configuration. Sets all credentials, paths, timezone, and scheduling for Bangalore (Asia/Kolkata, 8am default).
"""
import os
from dotenv import load_dotenv

load_dotenv()

APIFY_API_TOKEN = os.getenv('APIFY_API_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_FROM = os.getenv('TWILIO_WHATSAPP_FROM')  # e.g. whatsapp:+14155238886
TWILIO_WHATSAPP_TO = os.getenv('TWILIO_WHATSAPP_TO')
LOCATION = 'Bangalore'
TIMEZONE = os.getenv('TIMEZONE', 'Asia/Kolkata')
DAILY_RUN_TIME = os.getenv('DAILY_RUN_TIME', '08:00')
DATABASE_PATH = os.getenv('DATABASE_PATH', '/app/data/ideas.db')
LOG_FILE_PATH = os.getenv('LOG_FILE_PATH', '/app/data/logs/flashagent.log')
