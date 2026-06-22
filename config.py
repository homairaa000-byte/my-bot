import os

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # رابط Render
PORT = int(os.getenv("PORT", 10000))
