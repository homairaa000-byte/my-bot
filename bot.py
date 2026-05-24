import os
import sqlite3
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# ====== CONFIG ======
TOKEN = os.environ.get("BOT_TOKEN")
BASE_URL = os.environ.get("BASE_URL")  # https://your-app.onrender.com
PORT = int(os.environ.get("PORT", 10000))
WEBHOOK_PATH = f"/webhook/{TOKEN}"

# ====== FLASK ======
app = Flask(__name__)

# ====== TELEGRAM APP ======
application = Application.builder().token(TOKEN).build()

# ====== DB ======
conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    status TEXT
)
""")
conn.commit()


# ====== HELPERS ======
def is_admin_sync(user_id):
    # مبسط (بدون async مشاكل)
    ADMIN_IDS = os.environ.get("ADMIN_IDS", "")
    return str(user_id) in ADMIN_IDS.split(",")


def main_text():
    cursor.execute("SELECT name, status FROM users")
    rows = cursor.fetchall()

    text = "📋 قائمة التسجيل\n\n"

    statuses = ["register", "read", "listen", "excuse"]

    for st in statuses:
        text += f"📌 {st}:\n"
        for name, status in rows:
            if status == st:
                text += f"• {name}\n"
        text += "\n"

    return text


def keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✍ تسجيل", callback_data="register"),
            InlineKeyboardButton("❌ حذف", callback_data="remove")
        ],
        [
            InlineKeyboardButton("✅ قرأت", callback_data="read"),
            InlineKeyboardButton("🎧 مستمع", callback_data="listen")
        ],
        [
            InlineKeyboardButton("⛔ اعتذار", callback_data="excuse")
        ]
    ])


# ====== HANDLERS ======
async def start(update, context):
    await update.message.reply_text(main_text(), reply_markup=keyboard())


async def buttons(update, context):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    name = q.from_user.full_name
    data = q.data

    if data == "remove":
        cursor.execute("DELETE FROM users WHERE user_id=?", (uid,))

    elif data in ["register", "read", "listen", "excuse"]:
        cursor.execute("""
        INSERT OR REPLACE INTO users (user_id, name, status)
        VALUES (?, ?, ?)
        """, (uid, name, data))

    conn.commit()

    await q.edit_message_text(main_text(), reply_markup=keyboard())


async def block_links(update, context):
    text = update.message.text or ""
    if "http" in text or "t.me" in text:
        if not is_admin_sync(update.effective_user.id):
            await update.message.delete()


# ====== REGISTER HANDLERS ======
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(buttons))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, block_links))


# ====== WEBHOOK ======
@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.create_task(application.process_update(update))
    return "ok"


# ====== START ======
if __name__ == "__main__":
    import asyncio

    async def main():
        await application.initialize()
        await application.start()
        await application.bot.set_webhook(f"{BASE_URL}{WEBHOOK_PATH}")

    asyncio.run(main())

    app.run(host="0.0.0.0", port=PORT)
