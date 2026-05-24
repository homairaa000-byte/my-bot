import os
import sqlite3
import re
import asyncio
import threading

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
    filters,
    ContextTypes
)

# =====================
# الإعدادات
# =====================

TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

application = Application.builder().token(TOKEN).build()

# =====================
# قاعدة البيانات
# =====================

conn = sqlite3.connect(
    "students.db",
    check_same_thread=False
)

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
INSERT OR IGNORE INTO settings
VALUES ('locked', 'false')
""")

conn.commit()

# =====================
# دوال مساعدة
# =====================

def is_locked():
    result = cursor.execute(
        "SELECT value FROM settings WHERE key='locked'"
    ).fetchone()

    return result[0] == "true"


async def is_admin(user_id, chat_id):
    try:
        admins = await application.bot.get_chat_administrators(chat_id)

        return any(admin.user.id == user_id for admin in admins)

    except:
        return False


def get_text():

    cursor.execute(
        "SELECT name, status FROM students"
    )

    data = cursor.fetchall()

    text = """
🌸 خادم القرآن الرقمي

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
            for n in names:
                text += f"• {n}\n"
        else:
            text += "لا يوجد\n"

        text += "\n"

    text += "━━━━━━━━━━━━━━\n"

    if is_locked():
        text += "🔒 التسجيل مغلق"
    else:
        text += "🔓 التسجيل مفتوح"

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

        if is_locked():
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

# =====================
# /start
# =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        get_text(),
        reply_markup=await get_keyboard(update)
    )

# =====================
# الأزرار
# =====================

async def buttons(update, context):

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

    # قفل وفتح
    elif data == "toggle":

        if await is_admin(
            user
