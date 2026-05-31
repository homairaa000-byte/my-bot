import os
import logging
import sqlite3
import threading
from datetime import datetime
import pytz
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
logger = logging.getLogger("bot")

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL") 
PORT = int(os.getenv("PORT", 10000))

if not TOKEN or not WEBHOOK_URL:
    raise Exception("Missing BOT_TOKEN or WEBHOOK_URL")

DB = "bot.db"

# =========================
# قاعدة بيانات
# =========================
def db():
    return sqlite3.connect(DB, check_same_thread=False)

def init():
    with db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER,
            user_id INTEGER,
            name TEXT,
            status TEXT,
            PRIMARY KEY(chat_id, user_id)
        )
        """)

def set_user(chat_id, user_id, name, status):
    with db() as conn:
        conn.execute("""
        INSERT INTO users VALUES (?, ?, ?, ?)
        ON CONFLICT(chat_id, user_id)
        DO UPDATE SET name=excluded.name, status=excluded.status
        """, (chat_id, user_id, name, status))

def delete_user(chat_id, user_id):
    with db() as conn:
        conn.execute("DELETE FROM users WHERE chat_id=? AND user_id=?", (chat_id, user_id))

def reset_chat(chat_id):
    with db() as conn:
        conn.execute("DELETE FROM users WHERE chat_id=?", (chat_id,))

def fetch(chat_id):
    with db() as conn:
        return conn.execute("SELECT name, status FROM users WHERE chat_id=?", (chat_id,)).fetchall()

# =========================
# واجهة العرض
# =========================
def build(chat_id):
    data = fetch(chat_id)
    def group(status): return [n for n, s in data if s == status]
    def fmt(lst): return "لا يوجد" if not lst else "\n".join(f"{i+1}- {n}" for i, n in enumerate(lst))
    now = datetime.now(pytz.timezone("Africa/Tripoli")).strftime("%Y-%m-%d %H:%M")
    return f"📅 {now}\n\n📖 خادم القرآن الرقمي\n\n✍️ مسجلات:\n{fmt(group('register'))}\n\n🎧 مستمعات:\n{fmt(group('listener'))}\n\n⛔️ معتذرات:\n{fmt(group('excused'))}\n\n✅ قرأت:\n{fmt(group('read'))}"

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ سجل", callback_data="register"), InlineKeyboardButton("🎧 مستمعة", callback_data="listener")],
        [InlineKeyboardButton("⛔️ معتذرة", callback_data="excused"), InlineKeyboardButton("✅ قرأت", callback_data="read")],
        [InlineKeyboardButton("🧹 تصفير", callback_data="reset"), InlineKeyboardButton("❌ حذف اسمي", callback_data="remove")]
    ])

# =========================
# الأوامر
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(build(update.effective_chat.id), reply_markup=menu())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = q.message.chat_id
    user_id = q.from_user.id
    name = q.from_user.full_name
    data = q.data

    if data in ["register", "listener", "excused", "read"]: set_user(chat_id, user_id, name, data)
    elif data == "remove": delete_user(chat_id, user_id)
    elif data == "reset": reset_chat(chat_id)
    await q.edit_message_text(build(chat_id), reply_markup=menu())

# =========================
# تشغيل خادم الصحة والـ Webhook
# =========================
app_health = Flask(__name__)
@app_health.route('/')
def health(): return "Bot is live", 200

def main():
    init()
    # تشغيل خادم الصحة لـ Render
    threading.Thread(target=lambda: app_health.run(host="0.0.0.0", port=PORT), daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    
    # استخدام الـ Webhook المباشر
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}",
        url_path=TOKEN,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()
