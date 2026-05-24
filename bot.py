import os
import sqlite3
import re
import asyncio
from flask import Flask, request
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# =========================
# الإعدادات
# =========================

TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

application = Application.builder().token(TOKEN).build()

# =========================
# قاعدة البيانات
# =========================

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

cursor.execute("""
INSERT OR IGNORE INTO settings (key, value)
VALUES ('locked', 'false')
""")

conn.commit()

# =========================
# الدوال
# =========================

async def is_admin(user_id, chat_id):
    try:
        admins = await application.bot.get_chat_administrators(chat_id)
        return any(admin.user.id == user_id for admin in admins)
    except:
        return False


def registration_locked():
    result = cursor.execute(
        "SELECT value FROM settings WHERE key='locked'"
    ).fetchone()

    return result[0] == "true"


def get_status_text():
    cursor.execute("SELECT name, status FROM students")
    data = cursor.fetchall()

    text = """
السلام عليكم ورحمة الله وبركاته 🌸

📚 خادم القرآن الرقمي
━━━━━━━━━━━━━━

"""

    categories = {
        "register": "✍️ المسجلات",
        "read": "✅ قرأت",
        "listen": "🎧 مستمعات",
        "excuse": "⛔️ معتذرات"
    }

    for key, title in categories.items():

        text += f"{title}:\n"

        names = [n for n, s in data if s == key]

        if names:
            for name in names:
                text += f"• {name}\n"
        else:
            text += "لا يوجد\n"

        text += "\n"

    text += "━━━━━━━━━━━━━━\n"

    if registration_locked():
        text += "🔒 التسجيل مغلق حالياً\n"
    else:
        text += "🔓 التسجيل مفتوح\n"

    text += "\n🌷 بارك الله فيكن"

    return text


async def get_keyboard(update):

    keyboard = [
        [
            InlineKeyboardButton(
                "✍️ سجل إسمي",
                callback_data="register"
            ),
            InlineKeyboardButton(
                "❌ حذف إسمي",
                callback_data="remove"
            )
        ],
        [
            InlineKeyboardButton(
                "✅ قرأت",
                callback_data="read"
            ),
            InlineKeyboardButton(
                "🎧 مستمعة",
                callback_data="listen"
            )
        ],
        [
            InlineKeyboardButton(
                "⛔️ معتذرة",
                callback_data="excuse"
            )
        ]
    ]

    if await is_admin(
        update.effective_user.id,
        update.effective_chat.id
    ):

        if registration_locked():
            lock_text = "🔓 فتح التسجيل"
        else:
            lock_text = "🔒 قفل التسجيل"

        keyboard.append([
            InlineKeyboardButton(
                lock_text,
                callback_data="toggle"
            ),
            InlineKeyboardButton(
                "🗑 تصفير",
                callback_data="clear"
            )
        ])

    return InlineKeyboardMarkup(keyboard)

# =========================
# الأوامر
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        get_status_text(),
        reply_markup=await get_keyboard(update)
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id
    name = query.from_user.full_name
    data = query.data

    # حذف الاسم
    if data == "remove":

        cursor.execute(
            "DELETE FROM students WHERE user_id=?",
            (user_id,)
        )

    # قفل أو فتح
    elif data == "toggle":

        if not await is_admin(user_id, query.message.chat.id):
            return

        current = registration_locked()

        cursor.execute(
            "UPDATE settings SET value=? WHERE key='locked'",
            ("false" if current else "true",)
        )

    # تصفير
    elif data == "clear":

        if not await is_admin(user_id, query.message.chat.id):
            return

        cursor.execute("DELETE FROM students")

    # التسجيل
    elif data in ["register", "read", "listen", "excuse"]:

        if registration_locked():

            if not await is_admin(user_id, query.message.chat.id):

                await query.answer(
                    "⛔️ التسجيل مغلق",
                    show_alert=True
                )
                return

        cursor.execute(
            "INSERT OR REPLACE INTO students VALUES (?, ?, ?)",
            (user_id, name, data)
        )

    conn.commit()

    await query.edit_message_text(
        text=get_status_text(),
        reply_markup=await get_keyboard(update)
    )


# =========================
# حذف الروابط
# =========================

async def delete_links(update, context):

    if await is_admin(
        update.effective_user.id,
        update.effective_chat.id
    ):
        return

    text = update.message.text or ""

    if re.search(r"(https?://|t\.me|www\.)", text):

        await update.message.delete()

        await update.message.reply_text(
            "⛔️ يمنع إرسال الروابط"
        )

# =========================
# ربط المعالجات
# =========================

application.add_handler(
    CommandHandler("start", start)
)

application.add_handler(
    CallbackQueryHandler(buttons)
)

application.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        delete_links
    )
)

# =========================
# الصفحة الرئيسية
# =========================

@app.route("/")
def home():
    return "BOT IS RUNNING"

# =========================
# WEBHOOK
# =========================

@app.route("/webhook", methods=["POST"])
def webhook():

    update = Update.de_json(
        request.get_json(force=True),
        application.bot
    )

    asyncio.run(application.process_update(update))

    return "ok"

# =========================
# التشغيل
# =========================

if __name__ == "__main__":

    asyncio.run(application.initialize())

    app.run(
        host="0.0.0.0",
        port=PORT
        )
