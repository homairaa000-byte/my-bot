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
# إعدادات
# =========================

logging.basicConfig(level=logging.INFO)

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
# Telegram App
# =========================

application = Application.builder().token(TOKEN).build()

# =========================
# بيانات
# =========================

chat_data = {}


def get_data(chat_id):
    if chat_id not in chat_data:
        chat_data[chat_id] = {
            "registered": {},   # id -> name
            "readers": set(),   # ids
            "listeners": {},
            "excused": {},
            "blocked": set(),   # ids
            "blocked_names": {},
            "registration_open": True,
        }
    return chat_data[chat_id]


# =========================
# UI
# =========================

def menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✍️ سجل اسمي", callback_data="register"),
            InlineKeyboardButton("✅ قرأت", callback_data="read"),
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
# عرض القوائم
# =========================

def fmt(d):
    if not d:
        return "لا يوجد"
    return "\n".join(f"{i+1}- {name}" for i, name in enumerate(d.values()))


def build_text(chat_id):
    data = get_data(chat_id)

    tz = pytz.timezone("Africa/Tripoli")
    date_str = datetime.now(tz).strftime("%Y-%m-%d %H:%M")

    blocked_names = list(data["blocked_names"].values())

    return (
        f"📅 {date_str}\n\n"
        "خادم القرآن الرقمي 💫\n\n"
        f"✍️ المسجلات:\n{fmt(data['registered'])}\n\n"
        f"⛔️ المعتذرات:\n{fmt(data['excused'])}\n\n"
        f"🎧 المستمعات:\n{fmt(data['listeners'])}\n\n"
        f"🚫 المحظورات:\n{fmt({'x': n for n in blocked_names})}"
    )


# =========================
# Webhook setup (حل Conflict)
# =========================

async def setup_webhook():
    await application.initialize()

    # 🔥 مهم جدًا لمنع Conflict
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
# Callback
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

    # إزالة من كل القوائم
    def clear_user():
        data["registered"].pop(user_id, None)
        data["listeners"].pop(user_id, None)
        data["excused"].pop(user_id, None)
        data["readers"].discard(user_id)

    # ================= REGISTER =================
    if query.data == "register":
        if not data["registration_open"]:
            await query.answer("التسجيل مغلق", show_alert=True)
            return

        clear_user()
        data["registered"][user_id] = user_name

    # ================= READ TOGGLE =================
    elif query.data == "read":

        if user_id not in data["registered"]:
            await query.answer("سجلي اسمك أولاً", show_alert=True)
            return

        # 🔁 toggle
        if user_id in data["readers"]:
            data["readers"].remove(user_id)
        else:
            data["readers"].add(user_id)

    # ================= LISTENER =================
    elif query.data == "listener":
        clear_user()
        data["listeners"][user_id] = user_name

    # ================= EXCUSED =================
    elif query.data == "excused":
        clear_user()
        data["excused"][user_id] = user_name

    # ================= REMOVE =================
    elif query.data == "remove":
        clear_user()

    # ================= ADMIN =================
    elif query.data in ["reset", "toggle"]:

        # (هنا ممكن تضيف check admin لاحقًا)
        if query.data == "toggle":
            data["registration_open"] = not data["registration_open"]

        elif query.data == "reset":
            data["registered"].clear()
            data["listeners"].clear()
            data["excused"].clear()
            data["readers"].clear()

    await query.edit_message_text(
        build_text(chat_id),
        reply_markup=menu()
    )


# =========================
# تشغيل webhook
# =========================

if __name__ == "__main__":
    asyncio.run(setup_webhook())
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
