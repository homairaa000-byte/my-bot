import os
import logging
import asyncio
import threading
from flask import Flask, request
from datetime import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

# إعدادات التسجيل - مهم جداً لمراقبة الخطأ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL").rstrip("/")
PORT = int(os.environ.get("PORT", 10000))

# بناء التطبيق - تم تفعيل تحديثات متزامنة لضمان الاستقرار
application = Application.builder().token(TOKEN).concurrent_updates(True).build()
chat_data = {}

def get_data(chat_id):
    if chat_id not in chat_data:
        chat_data[chat_id] = {"registered": {}, "readers": set(), "listeners": {}, "excused": {}}
    return chat_data[chat_id]

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ سجل اسمي", callback_data="register"), InlineKeyboardButton("✅ قرأت", callback_data="read")],
        [InlineKeyboardButton("🎧 مستمعة", callback_data="listener"), InlineKeyboardButton("⛔️ معتذرة", callback_data="excused")],
        [InlineKeyboardButton("🧹 تصفير", callback_data="reset"), InlineKeyboardButton("❌ حذف", callback_data="remove")]
    ])

def fmt(d): return "لا يوجد" if not d else "\n".join(f"{i+1}- {n}" for i, n in enumerate(d.values()))
def fmt_set(s): return "لا يوجد" if not s else "\n".join(f"{i+1}- {uid}" for i, uid in enumerate(s))

def build_text(chat_id):
    data = get_data(chat_id)
    now = datetime.now(pytz.timezone("Africa/Tripoli")).strftime("%Y-%m-%d %H:%M")
    return (f"📅 {now}\n\nخادم القرآن الرقمي 💫\n\n✍️ المسجلات:\n{fmt(data['registered'])}\n\n"
            f"⛔️ المعتذرات:\n{fmt(data['excused'])}\n\n🎧 المستمعات:\n{fmt(data['listeners'])}\n\n"
            f"✅ قرأت:\n{fmt_set(data['readers'])}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # إرسال الرسالة مباشرة
    await context.bot.send_message(chat_id=update.effective_chat.id, text=build_text(update.effective_chat.id), reply_markup=menu())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    name = update.effective_user.full_name
    data = get_data(chat_id)
    
    if query.data == "register": data["registered"][user_id] = name
    elif query.data == "read":
        if user_id in data["readers"]: data["readers"].remove(user_id)
        else: data["readers"].add(user_id)
    elif query.data == "listener": data["listeners"][user_id] = name
    elif query.data == "excused": data["excused"][user_id] = name
    elif query.data == "remove": 
        data["registered"].pop(user_id, None); data["listeners"].pop(user_id, None); 
        data["excused"].pop(user_id, None); data["readers"].discard(user_id)
    elif query.data == "reset": 
        data["registered"].clear(); data["listeners"].clear(); 
        data["excused"].clear(); data["readers"].clear()
    
    # حذف الرسالة القديمة ثم إرسال الجديدة
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)
    except Exception as e:
        logger.warning(f"Delete message failed: {e}")
    
    await context.bot.send_message(chat_id=chat_id, text=build_text(chat_id), reply_markup=menu())

app = Flask(__name__)

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    # استخدام thread-safe لضمان عدم انقطاع المعالجة
    update = Update.de_json(data=request.get_json(force=True), bot=application.bot)
    asyncio.run_coroutine_threadsafe(application.process_update(update), application.bot_data['
