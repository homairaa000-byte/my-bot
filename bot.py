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
# Application
# =========================

application = Application.builder().token(TOKEN).build()


# =========================
# بيانات (ID + Name)
# =========================

chat_data = {}


def get_data(chat_id):
    if chat_id not in chat_data:
        chat_data[chat_id] = {
            "registered": {},   # id -> name
            "readers": {},      # id -> name
            "listeners": {},    # id -> name
            "excused": {},      # id -> name
            "blocked": set(),   # ids
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
            InlineKeyboardButton("✅ قرأت", callback_data="read"),
            InlineKeyboardButton("✍️ سجل اسمي", callback_data="register"),
        ],
        [
            InlineKeyboardButton("🎧 مستمعة", callback_data="listener"),
            InlineKeyboardButton("⛔️ معتذرة", callback_data="excused"),
        ],
        [
            InlineKeyboardButton("🧹 تصفير", callback_data="reset"),
            InlineKeyboardButton("🔒 قفل/فتح", callback_data="toggle"),
        ],
        [
            InlineKeyboardButton("❌ حذف اسمي", callback_data="remove")
        ]
    ])


# =========================
# عرض القوائم (بالأسماء)
# =========================

def format_dict(d):
    if not d:
        return "لا يوجد"
    return "\n".join(
        f"{i+1}- {name}"
        for i, name in enumerate(d.values())
    )


def build_text(chat_id):
    data = get_data(chat_id)

    tz = pytz.timezone("Africa/Tripoli")
    date_str = datetime.now(tz).strftime("%Y-%m-%d %H:%M")

    blocked_names = list(data["blocked_names"].values())

    return (
        f"📅 {date_str}\n\n"
        "خادم القرآن الرقمي 💫\n\n"
        f"✍️ المسجلات:\n{format_dict(data['registered'])}\n\n"
        f"⛔️ المعتذرات:\n{format_dict(data['excused'])}\n\n"
        f"🎧 المستمعات:\n{format_dict(data['listeners'])}\n\n"
        f"🚫 المحظورات:\n{blocked_names if blocked_names else 'لا يوجد'}"
    )


# =========================
# Webhook setup
# =========================

async def setup_webhook():
    await application.initialize()

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
# الأزرار
# =========================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name

    data = get_data(chat_id)

    # 🚫 حظر
    if user_id in data["blocked"]:
        await query.answer("أنتِ محظورة!", show_alert=True)
        return

    def remove_everywhere():
        data["registered"].pop(user_id, None)
        data["readers"].pop(user_id, None)
        data["listeners"].pop(user_id, None)
        data["excused"].pop(user_id, None)

    # ================= REGISTER =================
    if query.data == "register":

        if not data["registration_open"]:
            await query.answer("التسجيل مغلق", show_alert=True)
            return

        remove_everywhere()
        data["registered"][user_id] = user_name

    # ================= READ TOGGLE =================
    elif query.data == "read":

        if user_id not in data["registered"]:
            await query.answer("يجب التسجيل أولاً", show_alert=True)
            return

        if user_id in data["readers"]:
            del data["readers"][user_id]
            await query.answer("تم إزالة قر
