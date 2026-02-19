from os import getenv
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = getenv("BOT_TOKEN")
SERVER_IP = getenv("SERVER_IP")
ALERT_CHANNEL_ID = getenv("ALERT_CHANNEL_ID")
PING_USER_ID = getenv("PING_USER_ID")
