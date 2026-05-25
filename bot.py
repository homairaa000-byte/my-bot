import os
import sqlite3
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# =====================
# إعدادات
# =====================
TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

# =====================
# Telegram App
# =====================
application = Application.builder().token(TOKEN).build()

# =====================
# قاعدة البيانات
# =====================
conn = sqlite3.connect("students.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS students (user_id INTEGER PRIMARY KEY, name TEXT, status TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS banned (user_id INTEGER PRIMARY KEY, name TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")

cursor.execute("INSERT OR IGNORE INTO settings VALUES ('locked', 'false')")
conn.commit()

# =====================
# وظائف مساعدة
# =====================
def is_locked():
    return cursor.execute("SELECT value FROM settings WHERE key='locked'").fetchone()[0] == "true"


def get_status_text():
    cursor.execute("SELECT name, status FROM students")
    data = cursor.fetchall()

    cursor.execute("SELECT name FROM banned")
    banned_list = [r[0] for r in cursor.fetchall()]

    text = "📖 خادم القرآن الرقمي\n\n"

    categories = {
        "register": "✍️ المسجلات",
        "read": "✅ قرأت",
        "listen": "🎧 مستمعات",
        "excuse": "⛔️ معتذرات"
    }

    for key, title in categories.items():
        text += f"{title}:\n"
        names = [f"• {n}" for n, s in data if s == key]
        text += "\n".join(names) if names else "لا يوجد"
        text += "\n\n"

    text += "🚫 المحظورات:\n"
    text += "\n".join([f"• {n}" for n in banned_list]) if banned_list else "لا يوجد"

    return text


async def is_admin(user_id, chat_id):
    try:
        admins = await application.bot.get_chat_administrators(chat_id)
        return any(a.user.id == user_id for a in admins)
    except:
        return False


def keyboard(update):
    kb = [
        [InlineKeyboardButton("✍ تسجيل", callback_data="register"),
         InlineKeyboardButton("❌ حذف", callback_data="remove")],
        [InlineKeyboardButton("✅ قرأت", callback_data="read"),
         InlineKeyboardButton("🎧 مستمعة", callback_data="listen")],
        [InlineKeyboardButton("⛔ معتذرة", callback_data="excuse")]
    ]
    return InlineKeyboardMarkup(kb)

# =====================
# أوامر
# =====================
async def start(update, context):
    await update.message.reply_text(get_status_text(), reply_markup=keyboard(update))


async def handle_buttons(update, context):
    query = update.callback_query
    await query.answer()

    uid = query.from_user.id
    name = query.from_user.full_name
    data = query.data

    if data == "remove":
        cursor.execute("DELETE FROM students WHERE user_id=?", (uid,))
    else:
        if is_locked() and not await is_admin(uid, query.message.chat.id):
            await query.answer("التسجيل مقفل", show_alert=True)
            return

        cursor.execute(
            "INSERT OR REPLACE INTO students VALUES (?, ?, ?)",
            (uid, name, data)
        )

    conn.commit()
    await query.edit_message_text(get_status_text(), reply_markup=keyboard(update))


async def block_links(update, context):
    text = update.message.text or ""
    if "http" in text and not await is_admin(update.effective_user.id, update.effective_chat.id):
        await update.message.delete()
        await update.message.reply_text("⛔ الروابط ممنوعة")


# =====================
# Handlers
# =====================
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(handle_buttons))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, block_links))

# =====================
# Webhook route (IMPORTANT FIX)
# =====================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)

    # تشغيل مباشر بدون create_task (هذا سبب خطأك السابق)
    application.update_queue.put_nowait(update)

    return "ok", 200


@app.route("/")
def home():
    return "Bot is running", 200


# =====================
# تشغيل التطبيق
# =====================
if __name__ == "__main__":
    application.initialize()
    application.start()

    app.run(host="0.0.0.0", port=PORT)
