import os
import sqlite3
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

TOKEN = os.environ.get("BOT_TOKEN")
BASE_URL = os.environ.get("BASE_URL")  # https://your-app.onrender.com
PORT = int(os.environ.get("PORT", 10000))

# ================= DATABASE =================
conn = sqlite3.connect("students.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    status TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

cursor.execute("INSERT OR IGNORE INTO settings VALUES ('locked', 'false')")
conn.commit()

# ================= BOT APP =================
application = Application.builder().token(TOKEN).build()


# ================= HELPERS =================
def locked():
    return cursor.execute(
        "SELECT value FROM settings WHERE key='locked'"
    ).fetchone()[0] == "true"


def keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✍ تسجيل", callback_data="register"),
            InlineKeyboardButton("❌ حذف", callback_data="remove"),
        ],
        [
            InlineKeyboardButton("✅ قرأت", callback_data="read"),
            InlineKeyboardButton("🎧 مستمعات", callback_data="listen"),
        ],
        [
            InlineKeyboardButton("⛔ معتذرات", callback_data="excuse"),
        ],
    ])


def get_text():
    cursor.execute("SELECT name, status FROM students")
    data = cursor.fetchall()

    text = "📋 قائمة التسجيل\n\n"

    cats = {
        "register": "✍️ مسجلات",
        "read": "✅ قرأت",
        "listen": "🎧 مستمعات",
        "excuse": "⛔ معتذرات",
    }

    for key, title in cats.items():
        text += f"{title}:\n"
        users = [f"• {n}" for n, s in data if s == key]
        text += "\n".join(users) if users else "لا يوجد"
        text += "\n\n"

    return text


# ================= HANDLERS =================
async def start(update: Update, context):
    await update.message.reply_text(get_text(), reply_markup=keyboard())


async def buttons(update: Update, context):
    query = update.callback_query
    await query.answer()

    uid = query.from_user.id
    name = query.from_user.full_name
    data = query.data

    if data == "remove":
        cursor.execute("DELETE FROM students WHERE user_id=?", (uid,))

    elif data in ["register", "read", "listen", "excuse"]:
        if locked():
            await query.answer("التسجيل مقفول", show_alert=True)
            return

        cursor.execute(
            "INSERT OR REPLACE INTO students VALUES (?, ?, ?)",
            (uid, name, data)
        )

    conn.commit()

    await query.edit_message_text(get_text(), reply_markup=keyboard())


async def filter_links(update: Update, context):
    text = update.message.text or ""
    if "http" in text or "t.me" in text:
        await update.message.delete()


# ================= REGISTER =================
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(buttons))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, filter_links))


# ================= WEBHOOK START =================
async def main():
    await application.initialize()
    await application.start()

    webhook_url = f"{BASE_URL}/webhook"

    await application.bot.set_webhook(webhook_url)

    print("Bot is running with webhook:", webhook_url)

    # تشغيل السيرفر الداخلي للـ PTB
    await application.updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="webhook",
    )

    await application.updater.idle()


# ================= FLASK-FREE ENTRY =================
if __name__ == "__main__":
    asyncio.run(main())
