import os
import sqlite3
import asyncio
from datetime import datetime
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
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

conn.commit()

# =========================
# حالة التسجيل
# =========================

registration_open = True

# =========================
# الدوال
# =========================

def set_student(user_id, name, status):

    cursor.execute(
        "INSERT OR REPLACE INTO students VALUES (?, ?, ?)",
        (user_id, name, status)
    )

    conn.commit()

def remove_student(user_id):

    cursor.execute(
        "DELETE FROM students WHERE user_id=?",
        (user_id,)
    )

    conn.commit()

def clear_all():

    cursor.execute("DELETE FROM students")

    conn.commit()

def get_all():

    cursor.execute("SELECT name, status FROM students")

    return cursor.fetchall()

def get_status():

    date_now = datetime.now().strftime("%Y-%m-%d")

    data = get_all()

    text = f"""
🤖 بوت الأكاديمية

📅 {date_now}

🔒 التسجيل: {"مفتوح ✅" if registration_open else "مغلق ⛔"}

━━━━━━━━━━━━━━
"""

    categories = {
        "read": "📘 قرأت",
        "listen": "🎧 مستمعة",
        "excuse": "🚫 معتذرة"
    }

    for key, title in categories.items():

        text += f"\n{title}:\n"

        items = [n for n, s in data if s == key]

        if items:

            text += "\n".join([f"• {i}" for i in items])

        else:

            text += "لا يوجد"

        text += "\n"

    return text

# =========================
# الأزرار
# =========================

def main_keyboard():

    keyboard = [

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
                "🚫 معتذرة",
                callback_data="excuse"
            ),

            InlineKeyboardButton(
                "❌ حذف اسمي",
                callback_data="remove"
            )
        ],

        [
            InlineKeyboardButton(
                "🔒 فتح/قفل التسجيل",
                callback_data="toggle"
            )
        ],

        [
            InlineKeyboardButton(
                "🧹 تصفير القائمة",
                callback_data="clear"
            )
        ]

    ]

    return InlineKeyboardMarkup(keyboard)

# =========================
# أمر /start
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        get_status(),
        reply_markup=main_keyboard()
    )

# =========================
# الأزرار
# =========================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global registration_open

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id
    name = query.from_user.full_name
    data = query.data

    # التسجيل

    if data == "read":

        if registration_open:
            set_student(user_id, name, "read")

    elif data == "listen":

        if registration_open:
            set_student(user_id, name, "listen")

    elif data == "excuse":

        if registration_open:
            set_student(user_id, name, "excuse")

    # حذف الاسم

    elif data == "remove":

        remove_student(user_id)

    # فتح وإغلاق التسجيل

    elif data == "toggle":

        registration_open = not registration_open

    # تصفير القائمة

    elif data == "clear":

        clear_all()

    # تحديث الرسالة

    await query.edit_message_text(
        text=get_status(),
        reply_markup=main_keyboard()
    )

# =========================
# ربط الأوامر
# =========================

application.add_handler(
    CommandHandler("start", start)
)

application.add_handler(
    CallbackQueryHandler(buttons)
)

# =========================
# الصفحة الرئيسية
# =========================

@app.route("/")
def home():

    return "Bot is running!"

# =========================
# Webhook
# =========================

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():

    update = Update.de_json(
        request.get_json(force=True),
        application.bot
    )

    asyncio.run(
        application.process_update(update)
    )

    return "ok", 200

# =========================
# تشغيل البوت
# =========================

if __name__ == "__main__":

    asyncio.run(
        application.initialize()
    )

    app.run(
        host="0.0.0.0",
        port=PORT
    )
