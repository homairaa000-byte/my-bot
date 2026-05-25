import os
import sqlite3
import re
import asyncio
from flask import Flask, request

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# ================= CONFIG =================
TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

application = Application.builder().token(TOKEN).build()

# ================= DATABASE =================
conn = sqlite3.connect("students.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS students (user_id INTEGER PRIMARY KEY, name TEXT, status TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS banned (user_id INTEGER PRIMARY KEY, name TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
cursor.execute("INSERT OR IGNORE INTO settings VALUES ('locked','false')")
conn.commit()

# ================= ADMIN CHECK =================
async def is_admin(user_id, chat_id):
    try:
        admins = await application.bot.get_chat_administrators(chat_id)
        return any(a.user.id == user_id for a in admins)
    except:
        return False

# ================= TEXT =================
def get_status_text():
    cursor.execute("SELECT name, status FROM students")
    data = cursor.fetchall()

    cursor.execute("SELECT name FROM banned")
    banned = [r[0] for r in cursor.fetchall()]

    text = "السلام عليكم ورحمة الله وبركاته\n\n"

    cats = {
        "register": "✍️ المسجلات",
        "read": "✅ قرأت",
        "listen": "🎧 مستمعات",
        "excuse": "⛔️ معتذرات"
    }

    for key, title in cats.items():
        text += f"{title}:\n"
        names = [n for n, s in data if s == key]
        text += "\n".join(f"• {n}" for n in names) if names else "لا يوجد"
        text += "\n\n"

    text += "🚫 المحظورات:\n"
    text += "\n".join(f"• {n}" for n in banned) if banned else "لا يوجد"

    text += "\n\nخادم القرآن الرقمي\n"
    return text

# ================= KEYBOARD =================
async def get_keyboard(update):
    kb = [
        [
            InlineKeyboardButton("✍ سجل إسمي", callback_data="register"),
            InlineKeyboardButton("❌ إحذف إسمي", callback_data="remove")
        ],
        [
            InlineKeyboardButton("✅ قرأت", callback_data="read"),
            InlineKeyboardButton("🎧 مستمعات", callback_data="listen")
        ],
        [
            InlineKeyboardButton("⛔️ معتذرات", callback_data="excuse")
        ]
    ]

    if await is_admin(update.effective_user.id, update.effective_chat.id):
        kb.append([
            InlineKeyboardButton("🔒 قفل/فتح", callback_data="toggle"),
            InlineKeyboardButton("🗑 تصفير", callback_data="clear")
        ])

    return InlineKeyboardMarkup(kb)

# ================= START =================
async def start(update: Update, context):
    await update.message.reply_text(
        get_status_text(),
        reply_markup=await get_keyboard(update)
    )

# ================= LINK FILTER =================
async def link_filter(update: Update, context):
    if update.message and update.message.text:
        if re.search(r"http|www|t\.me", update.message.text):
            if not await is_admin(update.effective_user.id, update.effective_chat.id):
                await update.message.delete()
                await update.message.reply_text("⛔️⛔️⛔️ ممنوع إرسال روابط")

# ================= HANDLERS =================
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, link_filter))

# ================= WEBHOOK ROUTE =================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)

    # حل مشكلة asyncio في Render
    loop = asyncio.get_event_loop()
    loop.create_task(application.process_update(update))

    return "ok", 200

# ================= RUN =================
if __name__ == "__main__":
    print("Bot running via Webhook...")

    application.initialize()
    application.start()

    app.run(host="0.0.0.0", port=PORT)
