import os
import logging
import sqlite3
from datetime import datetime

import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# =========================
# إعدادات أساسية
# =========================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # مثال: https://your-app.onrender.com
PORT = int(os.getenv("PORT", 10000))

if not TOKEN or not WEBHOOK_URL:
    raise Exception("Missing BOT_TOKEN or WEBHOOK_URL")

DB_PATH = "bot.db"

# =========================
# قاعدة البيانات (SQLite)
# =========================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        chat_id INTEGER,
        user_id INTEGER,
        name TEXT,
        status TEXT,
        PRIMARY KEY(chat_id, user_id)
    )
    """)

    conn.commit()
    conn.close()

def set_status(chat_id, user_id, name, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
    INSERT INTO users (chat_id, user_id, name, status)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(chat_id, user_id)
    DO UPDATE SET name=excluded.name, status=excluded.status
    """, (chat_id, user_id, name, status))

    conn.commit()
    conn.close()

def remove_user(chat_id, user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    conn.commit()
    conn.close()

def clear_chat(chat_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE chat_id=?", (chat_id,))
    conn.commit()
    conn.close()

def get_all(chat_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, status FROM users WHERE chat_id=?", (chat_id,))
    rows = c.fetchall()
    conn.close()
    return rows

# =========================
# واجهة العرض
# =========================
def build_text(chat_id):
    data = get_all(chat_id)

    register = [n for n, s in data if s == "register"]
    listener = [n for n, s in data if s == "listener"]
    excused = [n for n, s in data if s == "excused"]
    read = [n for n, s in data if s == "read"]

    now = datetime.now(pytz.timezone("Africa/Tripoli")).strftime("%Y-%m-%d %H:%M")

    def fmt(lst):
        return "لا يوجد" if not lst else "\n".join(f"{i+1}- {n}" for i, n in enumerate(lst))

    return f"""
📅 {now}

📖 خادم القرآن الرقمي

✍️ المسجلات:
{fmt(register)}

🎧 المستمعات:
{fmt(listener)}

⛔️ المعتذرات:
{fmt(excused)}

✅ قرأت:
{fmt(read)}
""".strip()

def menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✍️ سجل", callback_data="register"),
            InlineKeyboardButton("🎧 مستمعة", callback_data="listener"),
        ],
        [
            InlineKeyboardButton("⛔️ معتذرة", callback_data="excused"),
            InlineKeyboardButton("✅ قرأت", callback_data="read"),
        ],
        [
            InlineKeyboardButton("🧹 تصفير", callback_data="reset"),
            InlineKeyboardButton("❌ حذف اسمي", callback_data="remove"),
        ],
    ])

# =========================
# الأوامر
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(build_text(chat_id), reply_markup=menu())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    user_id = query.from_user.id
    name = query.from_user.full_name

    data = query.data

    if data in ["register", "listener", "excused", "read"]:
        set_status(chat_id, user_id, name, data)

    elif data == "remove":
        remove_user(chat_id, user_id)

    elif data == "reset":
        clear_chat(chat_id)

    await query.edit_message_text(
        text=build_text(chat_id),
        reply_markup=menu()
    )

# =========================
# تشغيل البوت (احترافي)
# =========================
def main():
    init_db()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))

    # Webhook احترافي بدون Flask
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"{WEBHOOK_URL}/",
        url_path=TOKEN,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()
