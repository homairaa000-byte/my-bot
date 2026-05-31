import os
import logging
import asyncio
import threading
from flask import Flask, request
from datetime import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

# =========================
# إعدادات (كما هي)
# =========================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TOKEN or not WEBHOOK_URL:
    raise Exception("Missing BOT_TOKEN or WEBHOOK_URL")

WEBHOOK_URL = WEBHOOK_URL.rstrip("/")
PORT = int(os.environ.get("PORT", 10000))

# =========================
# Telegram App (بدون run_webhook لنتجنب الحظر)
# =========================
application = (
    Application.builder()
    .token(TOKEN)
    .concurrent_updates(True)
    .build()
)

# =========================
# بيانات (RAM) - كما هي
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
# UI & التنسيق - كما هي
# =========================
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ سجل اسمي", callback_data="register"), InlineKeyboardButton("✅ قرأت", callback_data="read")],
        [InlineKeyboardButton("🎧 مستمعة", callback_data="listener"), InlineKeyboardButton("⛔️ معتذرة", callback_data="excused")],
        [InlineKeyboardButton("🧹 تصفير", callback_data="reset"), InlineKeyboardButton("🔒 قفل/فتح", callback_data="toggle")],
        [InlineKeyboardButton("❌ حذف", callback_data="remove")]
    ])

def fmt(d): return "لا يوجد" if not d else "\n".join(f"{i+1}- {n}" for i, n in enumerate(d.values()))
def fmt_set(s): return "لا يوجد" if not s else "\n".join(f"{i+1}- {uid}" for i, uid in enumerate(s))

def build_text(chat_id):
    data = get_data(chat_id)
    now = datetime.now(pytz.timezone("Africa/Tripoli")).strftime("%Y-%m-%d %H:%M")
    return (f"📅 {now}\n\nخادم القرآن الرقمي 💫\n\n✍️ المسجلات:\n{fmt(data['registered'])}\n\n"
            f"⛔️ المعتذرات:\n{fmt(data['excused'])}\n\n🎧 المستمعات:\n{fmt(data['listeners'])}\n\n"
            f"✅ قرأت:\n{fmt_set(data['readers'])}")

# =========================
# Callback Handler - كما هو
# =========================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query: return
    await query.answer()
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    name = update.effective_user.full_name
    data = get_data(chat_id)
    if user_id in data["blocked"]:
        await query.answer("أنت محظورة", show_alert=True)
        return
    def clear():
        data["registered"].pop(user_id, None); data["listeners"].pop(user_id, None)
        data["excused"].pop(user_id, None); data["readers"].discard(user_id)
    try:
        if query.data == "register":
            if not data["registration_open"]: await query.answer("التسجيل مغلق", show_alert=True)
            else: clear(); data["registered"][user_id] = name
        elif query.data == "read":
            if user_id not in data["registered"]: await query.answer("سجل اسمك أولاً", show_alert=True)
            else:
                if user_id in data["readers"]: data["readers"].remove(user_id)
                else: data["readers"].add(user_id)
        elif query.data == "listener": clear(); data["listeners"][user_id] = name
        elif query.data == "excused": clear(); data["excused"][user_id] = name
        elif query.data == "remove": clear()
        elif query.data == "reset": data["registered"].clear(); data["listeners"].clear(); data["excused"].clear(); data["readers"].clear()
        elif query.data == "toggle": data["registration_open"] = not data["registration_open"]
        await query.edit_message_text(build_text(chat_id), reply_markup=menu())
    except Exception as e: logger.error(f"Callback error: {e}")

# =========================
# الربط مع FLASK (حل مشكلة التوقف)
# =========================
app = Flask(__name__)

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(data=request.get_json(force=True), bot=application.bot)
    asyncio.run_coroutine_threadsafe(application.process_update(update), application.bot_data['loop'])
    return "OK", 200

@app.route("/")
def index(): return "Bot is Active", 200

async def startup():
    application.add_handler(CallbackQueryHandler(buttons))
    await application.initialize()
    await application.start()
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook/{TOKEN}")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    application.bot_data['loop'] = loop
    threading.Thread(target=lambda: loop.run_until_complete(startup()), daemon=True).start()
    app.run(host="0.0.0.0", port=PORT)
