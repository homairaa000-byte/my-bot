import os
import sqlite3
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# ================== CONFIG ==================
TOKEN = os.environ.get("BOT_TOKEN")
BASE_URL = os.environ.get("BASE_URL")  # https://your-app.onrender.com
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

application = (
    Application.builder()
    .token(TOKEN)
    .build()
)

# ================== DATABASE ==================
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

# ================== HELPERS ==================
def is_locked():
    return cursor.execute(
        "SELECT value FROM settings WHERE key='locked'"
    ).fetchone()[0] == "true"


async def is_admin(user_id, chat_id):
    try:
        admins = await application.bot.get_chat_administrators(chat_id)
        return any(a.user.id == user_id for a in admins)
    except:
        return False


def get_text():
    cursor.execute("SELECT name, status FROM students")
    data = cursor.fetchall()

    text = "📋 قائمة التسجيل\n\n"

    categories = {
        "register": "✍️ مسجلات",
        "read": "✅ قرأت",
        "listen": "🎧 مستمعات",
        "excuse": "⛔️ معتذرات",
    }

    for key, title in categories.items():
        text += f"{title}:\n"
        users = [f"• {n}" for n, s in data if s == key]
        text += "\n".join(users) if users else "لا يوجد"
        text += "\n\n"

    return text


def keyboard(update):
    kb = [
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
    ]

    return InlineKeyboardMarkup(kb)


# ================== HANDLERS ==================
async def start(update, context):
    await update.message.reply_text(get_text(), reply_markup=keyboard(update))


async def buttons(update, context):
    query = update.callback_query
    await query.answer()

    uid = query.from_user.id
    name = query.from_user.full_name
    data = query.data

    if data == "remove":
        cursor.execute("DELETE FROM students WHERE user_id=?", (uid,))

    elif data in ["register", "read", "listen", "excuse"]:
        if is_locked() and not await is_admin(uid, query.message.chat.id):
            await query.answer("التسجيل مقفول", show_alert=True)
            return

        cursor.execute(
            "INSERT OR REPLACE INTO students VALUES (?, ?, ?)",
            (uid, name, data)
        )

    conn.commit()

    await query.edit_message_text(
        get_text(),
        reply_markup=keyboard(update)
    )


async def filter_links(update, context):
    text = update.message.text or ""
    if "http" in text or "t.me" in text:
        await update.message.delete()


# ================== REGISTER HANDLERS ==================
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(buttons))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, filter_links))


# ================== WEBHOOK ==================
@app.route("/")
def home():
    return "Bot is running", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.create_task(application.process_update(update))
    return "ok", 200


# ================== START ==================
if __name__ == "__main__":
    application.initialize()

    # تشغيل webhook تلقائيًا عند الإقلاع
    if BASE_URL:
        import requests
        requests.get(
            f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={
