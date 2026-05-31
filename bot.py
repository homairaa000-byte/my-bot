import os
import logging
import asyncio
from datetime import datetime

import pytz
from flask import Flask, request

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# =========================
# الإعدادات
# =========================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TOKEN:
    raise Exception("BOT_TOKEN missing")

if not WEBHOOK_URL:
    raise Exception("WEBHOOK_URL missing")


# =========================
# Flask
# =========================

app = Flask(__name__)

# =========================
# Application (IMPORTANT FIX)
# =========================

application = Application.builder().token(TOKEN).build()

# =========================
# بيانات
# =========================

chat_data = {}


def get_data(chat_id):
    if chat_id not in chat_data:
        chat_data[chat_id] = {
            "registered": [],
            "readers": set(),
            "listeners": set(),
            "excused": set(),
            "blocked": set(),
            "blocked_names": {},
            "registration_open": True,
        }
    return chat_data[chat_id]


# =========================
# القائمة
# =========================

def menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ قرأت", "read"),
            InlineKeyboardButton("✍️ سجل اسمي", "register"),
        ],
        [
            InlineKeyboardButton("🎧 مستمعة", "listener"),
            InlineKeyboardButton("⛔️ معتذرة", "excused"),
        ],
        [
            InlineKeyboardButton("🧹 تصفير", "reset"),
            InlineKeyboardButton("🔒 قفل/فتح", "toggle"),
        ],
        [
            InlineKeyboardButton("❌ حذف اسمي", "remove")
        ]
    ])


# =========================
# النص
# =========================

def build_text(chat_id):
    data = get_data(chat_id)

    tz = pytz.timezone("Africa/Tripoli")
    date_str = datetime.now(tz).strftime("%Y-%m-%d %H:%M")

    blocked_names = list(data["blocked_names"].values())

    return (
        f"📅 {date_str}\n\n"
        "خادم القرآن الرقمي 💫\n\n"
        f"المسجلات: {len(data['registered'])}\n"
        f"المعتذرات: {len(data['excused'])}\n"
        f"المستمعات: {len(data['listeners'])}\n"
        f"المحظورات: {len(blocked_names)}"
    )


# =========================
# حذف webhook القديم (مهم جدًا)
# =========================

async def setup_webhook():
    await application.initialize()

    # 🔥 يمنع Conflict 100%
    await application.bot.delete_webhook(drop_pending_updates=True)

    await application.bot.set_webhook(
        url=f"{WEBHOOK_URL}/webhook/{TOKEN}"
    )

    await application.start()


# =========================
# Flask webhook
# =========================

@app.post(f"/webhook/{TOKEN}")
def webhook():

    update = Update.de_json(
        request.get_json(force=True),
        application.bot,
    )

    asyncio.run(application.process_update(update))

    return "OK"


@app.route("/")
def home():
    return "Bot is running!"


# =========================
# تشغيل السيرفر
# =========================

if __name__ == "__main__":

    # تشغيل webhook أولاً
    asyncio.run(setup_webhook())

    # تشغيل flask
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
    )
