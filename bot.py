import os
import sqlite3
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

# Telegram Application
application = Application.builder().token(TOKEN).build()

# DB
conn = sqlite3.connect("students.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS students (user_id INTEGER PRIMARY KEY, name TEXT, status TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS banned (user_id INTEGER PRIMARY KEY, name TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
cursor.execute("INSERT OR IGNORE INTO settings VALUES ('locked', 'false')")
conn.commit()

# ---------- Helpers ----------
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

    text = "📚 خادم القرآن الرقمي\n\nقائمة التسجيل:\n\n"

    cats = {
        "register": "✍️ المسجلات",
        "read": "✅ قرأت",
        "listen": "🎧 مستمعات",
        "excuse": "⛔️ معتذرات"
    }

    for key, title in cats.items():
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
            InlineKeyboardButton("✍ سجل إسمي", callback_data="register"),
            InlineKeyboardButton("❌ حذف", callback_data="remove")
        ],
        [
            InlineKeyboardButton("✅ قرأت", callback_data="read"),
            InlineKeyboardButton("🎧 مستمعات", callback_data="listen")
        ],
        [InlineKeyboardButton("⛔️ معتذرات", callback_data="excuse")]
    ]

    if await is_admin(update.effective_user.id, update.effective_chat.id):
        locked = cursor.execute("SELECT value FROM settings WHERE key='locked'").fetchone()[0]
        status = "🔓 فتح التسجيل" if locked == "true" else "🔒 قفل التسجيل"

        kb.append([
            InlineKeyboardButton(status, callback_data="toggle"),
            InlineKeyboardButton("🗑 تصفير", callback_data="clear")
        ])

    return InlineKeyboardMarkup(kb)


# ---------- Handlers ----------
async def start(update, context):
    await update.message.reply_text(
        get_status_text(),
        reply_markup=await get_keyboard(update)
    )


async def filter_links(update, context):
    text = update.message.text or ""
    if "http" in text or "t.me" in text or "www" in text:
        await update.message.delete()
        await update.message.reply_text("⛔️ الروابط ممنوعة")


async def buttons(update, context):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    name = q.from_user.full_name
    data = q.data

    locked = cursor.execute("SELECT value FROM settings WHERE key='locked'").fetchone()[0]

    if data == "toggle":
        new = "false" if locked == "true" else "true"
        cursor.execute("UPDATE settings SET value=? WHERE key='locked'", (new,))

    elif data == "clear":
        cursor.execute("DELETE FROM students")

    elif data == "remove":
        cursor.execute("DELETE FROM students WHERE user_id=?", (uid,))

    elif data in ["register", "read", "listen", "excuse"]:
        if locked == "true":
            await q.answer("التسجيل مغلق", show_alert=True)
            return
        cursor.execute(
            "INSERT OR REPLACE INTO students VALUES (?, ?, ?)",
            (uid, name, data)
        )

    conn.commit()

    await q.edit_message_text(
        get_status_text(),
        reply_markup=await get_keyboard(update)
    )


# ---------- register handlers ----------
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, filter_links))
application.add_handler(CallbackQueryHandler(buttons))


# ---------- WEBHOOK ----------
@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)

    # ✔ الحل الصحيح (بدون asyncio مشاكل)
    application.update_queue.put_nowait(update)

    return "ok", 200


# ---------- START ----------
if __name__ == "__main__":
    application.run_polling(close_loop=False)
