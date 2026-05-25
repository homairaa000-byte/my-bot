import os
import sqlite3
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.environ.get("BOT_TOKEN")
RENDER_URL = os.environ.get("RENDER_URL")  # مثال: https://xxxx.onrender.com
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

# ---------------- BOT ----------------
application = (
    Application.builder()
    .token(TOKEN)
    .build()
)

# ---------------- DB ----------------
conn = sqlite3.connect("students.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS students (user_id INTEGER PRIMARY KEY, name TEXT, status TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS banned (user_id INTEGER PRIMARY KEY, name TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
cursor.execute("INSERT OR IGNORE INTO settings VALUES ('locked', 'false')")
conn.commit()


# ---------------- HELPERS ----------------
async def is_admin(user_id, chat_id):
    try:
        admins = await application.bot.get_chat_administrators(chat_id)
        return any(a.user.id == user_id for a in admins)
    except:
        return False


def get_status_text():
    cursor.execute("SELECT name, status FROM students")
    data = cursor.fetchall()

    cursor.execute("SELECT name FROM banned")
    banned = [x[0] for x in cursor.fetchall()]

    text = "📋 قائمة الأدوار\n\n"

    categories = {
        "register": "✍️ المسجلات",
        "read": "✅ قرأت",
        "listen": "🎧 مستمعات",
        "excuse": "⛔ معتذرات",
    }

    for key, title in categories.items():
        text += f"{title}:\n"
        names = [f"• {n}" for n, s in data if s == key]
        text += "\n".join(names) if names else "لا يوجد"
        text += "\n\n"

    text += "🚫 المحظورات:\n"
    text += "\n".join(banned) if banned else "لا يوجد"

    return text


async def get_keyboard(update):
    kb = [
        [
            InlineKeyboardButton("✍ سجل", callback_data="register"),
            InlineKeyboardButton("❌ حذف", callback_data="remove"),
        ],
        [
            InlineKeyboardButton("✅ قرأت", callback_data="read"),
            InlineKeyboardButton("🎧 مستمعات", callback_data="listen"),
        ],
        [InlineKeyboardButton("⛔ معتذرات", callback_data="excuse")],
    ]

    admin = await is_admin(update.effective_user.id, update.effective_chat.id)

    if admin:
        locked = cursor.execute("SELECT value FROM settings WHERE key='locked'").fetchone()[0]

        kb.append([
            InlineKeyboardButton(
                "🔓 فتح" if locked == "true" else "🔒 قفل",
                callback_data="toggle",
            ),
            InlineKeyboardButton("🗑 تصفير", callback_data="clear"),
        ])

    return InlineKeyboardMarkup(kb)


# ---------------- HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        get_status_text(),
        reply_markup=await get_keyboard(update),
    )


async def link_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    if "http" in text or "t.me" in text:
        if not await is_admin(update.effective_user.id, update.effective_chat.id):
            await update.message.delete()


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    name = q.from_user.full_name
    data = q.data

    if data == "toggle":
        val = cursor.execute("SELECT value FROM settings WHERE key='locked'").fetchone()[0]
        cursor.execute("UPDATE settings SET value=? WHERE key='locked'", ("false" if val == "true" else "true",))

    elif data == "clear":
        cursor.execute("DELETE FROM students")

    elif data == "remove":
        cursor.execute("DELETE FROM students WHERE user_id=?", (uid,))

    elif data in ["register", "read", "listen", "excuse"]:
        locked = cursor.execute("SELECT value FROM settings WHERE key='locked'").fetchone()[0]

        if locked == "true":
            await q.answer("التسجيل مقفل", show_alert=True)
            return

        cursor.execute(
            "INSERT OR REPLACE INTO students VALUES (?, ?, ?)",
            (uid, name, data),
        )

    conn.commit()

    await q.edit_message_text(
        get_status_text(),
        reply_markup=await get_keyboard(update),
    )


# ---------------- REGISTER HANDLERS ----------------
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(buttons))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, link_filter))


# ---------------- WEBHOOK ----------------
@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "OK"


# ---------------- START ----------------
if __name__ == "__main__":
    application.run_polling()
