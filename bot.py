import os
import logging
from datetime import datetime
import pytz
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, filters

# إعداد السيرفر الوهمي لـ Render
app = Flask(__name__)
@app.route('/')
def index(): return "Bot is running!"
def run(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN: raise Exception("BOT_TOKEN missing")

chat_data = {}

def get_data(chat_id):
    if chat_id not in chat_data:
        chat_data[chat_id] = {
            "registered": [], "readers": set(), "listeners": set(),
            "excused": set(), "blocked": set(), "registration_open": True
        }
    return chat_data[chat_id]

def menu():
    keyboard = [
        [InlineKeyboardButton("✅ قرأت", callback_data="read"), InlineKeyboardButton("✍️ سجل اسمي", callback_data="register")],
        [InlineKeyboardButton("🎧 مستمعة", callback_data="listener"), InlineKeyboardButton("⛔️ معتذرة", callback_data="excused")],
        [InlineKeyboardButton("🧹 تصفير", callback_data="reset"), InlineKeyboardButton("🔒 قفل/فتح", callback_data="toggle")],
        [InlineKeyboardButton("❌ حذف اسمي", callback_data="remove")]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_text(chat_id):
    data = get_data(chat_id)
    tz = pytz.timezone("Africa/Tripoli")
    date_str = datetime.now(tz).strftime("%Y-%m-%d %H:%M")
    status = "🔓 مفتوح" if data["registration_open"] else "🔒 مغلق"

    def format_list(items, is_registered=False):
        if not items: return "لا يوجد"
        return "\n".join([f"{i+1}- {name}{' ✅' if (is_registered and name in data['readers']) else ''}" 
                          for i, name in enumerate(items) if name not in data["blocked"]])

    return (
        "السلام عليكم ورحمة الله وبركاته 🌿\n\n"
        f"📅 {date_str}\n\nخادم القرآن الرقمي 💫\n\n"
        f"التسجيل {status}\n\nقائمة تسجيل الأدوار 📝\n\n"
        f"✍️ المسجلات:\n{format_list(data['registered'], True)}\n\n"
        f"⛔️ المعتذرات:\n{format_list(list(data['excused']))}\n\n"
        f
