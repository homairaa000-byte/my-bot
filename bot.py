import os
import logging
import asyncio
from datetime import datetime

import pytz
from flask import Flask, request

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

# =========================
# إعدادات
# =========================

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TOKEN or not WEBHOOK_URL:
    raise Exception("Missing BOT_TOKEN or WEBHOOK_URL")

# تنظيف الرابط
WEBHOOK_URL = WEBHOOK_URL.rstrip("/")

# =========================
# Flask
# =========================

app = Flask(__name__)

# =========================
# Telegram Application
# =========================

application = Application.builder().token(TOKEN).build()

# =========================
# بيانات
# =========================

chat_data = {}


def get_data(chat_id):
    if chat_id not in chat_data:
        chat_data[chat_id] = {
            "registered": {},
            "readers": set(),
            "listeners": {},
            "excused": {},
            "blocked": set(),
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
        [InlineKeyboardButton("❌ حذف", callback_data="remove")]
    ])


# =========================
# تنسيق
# =========================

def fmt(d):
    return "لا يوجد" if not d else "\n".join(f"{i+1}- {name}" for i, name in enumerate(d.values()))


def fmt_set(s):
    return "لا يوجد" if not s else "\n".join(f"{i+1}- {uid}" for i, uid in enumerate(s))


def build_text(chat_id):
    data = get_data(chat_id)

    now = datetime.now(pytz.timezone("Africa/Tripoli")).strftime("%Y-%m-%d %H:%M")

    return (
        f"📅 {now}\n\n"
        "خادم القرآن الرقمي 💫\n\n"
        f"✍️ المسجلات:\n{fmt(data['registered'])}\n\n"
        f"⛔️ المعتذرات:\n{fmt(data['excused'])}\n\n"
        f"🎧 المستمعات:\n{fmt(data['listeners'])}\n\n"
        f"✅ قرأت:\n{fmt_set(data['readers'])}"
    )


# =========================
# Callback handler
# =========================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    name = update.effective_user.full_name

    data = get_data(chat_id)

    if user_id in data["blocked"]:
        await query.answer("أنت محظورة", show_alert=True)
        return

    def clear():
        data["registered"].pop(user_id, None)
        data["listeners"].pop(user_id, None)
        data["excused"].pop(user_id, None)
        data["readers"].discard(user_id)

    if query.data == "register":
        if not data["registration_open"]:
            await query.answer("التسجيل مغلق", show_alert=True)
            return
        clear()
        data["registered"][user_id] = name

    elif query.data == "read":
        if user_id not in data["registered"]:
            await query.answer("سجلي اسمك أولاً", show_alert=True)
            return

        if user_id in data["readers"]:
            data["readers"].remove(user_id)
            await query.answer("تم إلغاء قرأت")
        else:
            data["readers"].add(user_id)
            await query.answer("تم تسجيل قرأت")

    elif query.data == "listener":
        clear()
        data["listeners"][user_id] = name

    elif query.data == "excused":
        clear()
        data["excused"][user_id] = name

    elif query.data == "remove":
        clear()

    elif query.data == "reset":
        data["registered"].clear()
        data["listeners"].clear()
        data["excused"].clear()
        data["readers"].clear()

    elif query.data == "toggle":
        data["registration_open"] = not data["registration_open"]

    await query.edit_message_text(
        build_text(chat_id),
        reply_markup=menu()
    )


# =========================
# webhook setup (FIXED)
# =========================

async def setup_webhook():
    await application.initialize()

    await application.bot.delete_webhook(drop_pending_updates=True)

    await application.bot.set_webhook(
        url=f"{WEBHOOK_URL}/webhook/{TOKEN}"
    )

    # مهم جدًا
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)


# =========================
# Flask webhook (FIXED بدون asyncio.run)
# =========================

@app.post(f"/webhook/{TOKEN}")
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)

    # بدل asyncio.run ❌
    application.create_task(application.process_update(update))

    return "OK"


@app.route("/")
def home():
    return "Bot is running!"


# =========================
# تشغيل
# =========================

if __name__ == "__main__":
    application.add_handler(CallbackQueryHandler(buttons))

    asyncio.run(setup_webhook())

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
