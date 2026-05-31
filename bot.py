import os
import logging
import asyncio
from flask import Flask, request
from datetime import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

# إعداد السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL").rstrip("/")
PORT = int(os.environ.get("PORT", 10000))

# تهيئة التطبيق
application = Application.builder().token(TOKEN).build()
chat_data = {}

def get_data(chat_id):
    if chat_id not in chat_data:
        chat_data[chat_id] = {"status": {}, "readers": set()}
    return chat_data[chat_id]

# تنسيق القوائم
def fmt_status(data, status_type):
    names = [name for uid, (name, s) in data["status"].items() if s == status_type]
    return "لا يوجد" if not names else "\n".join(f"{i+1}- {n}" for i, n in enumerate(names))

def fmt_readers(data):
    return "لا يوجد" if not data["readers"] else "\n".join(f"{i+1}- {n}" for i, n in enumerate(data["readers"]))

def build_text(chat_id):
    data = get_data(chat_id)
    now = datetime.now(pytz.timezone("Africa/Tripoli")).strftime("%Y-%m-%d %H:%M")
    return (f"📅 {now}\n\nخادم القرآن الرقمي 💫\n\n"
            f"✍️ المسجلات:\n{fmt_status(data, 'register')}\n\n"
            f"⛔️ المعتذرات:\n{fmt_status(data, 'excused')}\n\n"
            f"🎧 المستمعات:\n{fmt_status(data, 'listener')}\n\n"
            f"✅ قرأت:\n{fmt_readers(data)}")

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ سجل", callback_data="register"), InlineKeyboardButton("🎧 مستمعة", callback_data="listener")],
        [InlineKeyboardButton("⛔️ معتذرة", callback_data="excused"), InlineKeyboardButton("✅ قرأت", callback_data="read")],
        [InlineKeyboardButton("🧹 تصفير", callback_data="reset"), InlineKeyboardButton("❌ حذف اسمي", callback_data="remove")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(build_text(update.effective_chat.id), reply_markup=menu())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    name = update.effective_user.full_name
    data = get_data(chat_id)
    
    if query.data in ["register", "listener", "excused"]:
        # تحديث الحالة (ينقل العضوة من حالة لأخرى تلقائياً)
        data["status"][user_id] = (name, query.data)
    elif query.data == "read":
        if name in data["readers"]: data["readers"].remove(name)
        else: data["readers"].add(name)
    elif query.data == "remove":
        data["status"].pop(user_id, None)
        data["readers"].discard(name)
    elif query.data == "reset":
        data["status"].clear()
        data["readers"].clear()
    
    await query.edit_message_text(text=build_text(chat_id), reply_markup=menu())

# الربط مع Flask
app = Flask(__name__)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run_coroutine_threadsafe(application.process_update(update), loop)
    return "OK", 200

async def setup_bot():
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(buttons))
    await application.initialize()
    await application.start()
    await application.bot.set_webhook(f"{WEBHOOK_URL}/webhook/{TOKEN}")

if __name__ == "__main__":
    loop.run_until_complete(setup_bot())
    app.run(host="0.0.0.0", port=PORT)
