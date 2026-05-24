import os
import sqlite3
import re
import asyncio
import threading

from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# =========================
# الإعدادات الأساسية
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
CREATE TABLE IF NOT EXISTS banned (
    user_id INTEGER PRIMARY KEY,
    name TEXT
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
# دوال مساعدة
# =========================

async def is_admin(user_id, chat_id):
    try:
        admins = await application.bot.get_chat_administrators(chat_id)
        return any(admin.user.id == user_id for admin in admins)
    except:
        return False


def is_locked():
    result = cursor.execute(
        "SELECT value FROM settings WHERE key='locked'"
    ).fetchone()

    return result and result[0] == "true"


def get_status_text():
    cursor.execute("SELECT name, status FROM students")
    data = cursor.fetchall()

    cursor.execute("SELECT name FROM banned")
    banned_list = [row[0] for row in cursor.fetchall()]

    text = (
        "🌸 السلام عليكم ورحمة الله وبركاته 🌸\n\n"
        "📚 خادم القرآن الرقمي\n"
        "📋 قائمة تسجيل الأدوار\n\n"
    )

    categories = {
        "register": "✍️ المسجلات",
        "read": "✅ قرأت",
        "listen": "🎧 مستمعات",
        "excuse": "⛔️ معتذرات"
    }

    for key, title in categories.items():
        text += f"{title}:\n"

        names = []

        for name, status in data:
            if status == key:
                if key == "register":
                    names.append(f"• {name}")
                else:
                    names.append(f"• {name}")

        text += "\n".join(names) if names else "لا يوجد"
        text += "\n\n"

    text += "🚫 المحظورات:\n"

    if banned_list:
        text += "\n".join([f"• {name}" for name in banned_list])
    else:
        text += "لا يوجد"

    text += (
        "\n\n"
        "📖 خذِ الكتاب بقوة، واجعليه من أولويات يومك\n"
        "📚 واقرئي تفسيره واعملي به، وأنتِ الرابحة بإذن الله\n\n"
        "🌸 السلام عليكم ورحمة الله وبركاته 🌸"
    )

    return text


async def get_keyboard(update):
    keyboard = [
        [
            InlineKeyboardButton("✍️ سجل إسمي", callback_data="register"),
            InlineKeyboardButton("❌ إحذف إسمي", callback_data="remove")
        ],
        [
            InlineKeyboardButton("✅ قرأت", callback_data="read"),
            InlineKeyboardButton("🎧 مستمعة", callback_data="listen")
        ],
        [
            InlineKeyboardButton("⛔️ معتذرة", callback_data="excuse")
        ]
    ]

    if await is_admin(
        update.effective_user.id,
        update.effective_chat.id
    ):
        lock_text = (
            "🔓 فتح التسجيل"
            if is_locked()
            else "🔒 قفل التسجيل"
        )

        keyboard.append([
            InlineKeyboardButton(lock_text, callback_data="toggle"),
            InlineKeyboardButton("🗑 تصفير القائمة", callback_data="clear")
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

# =========================
# حذف الروابط
# =========================

async def link_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    text = update.message.text or ""

    has_link = re.search(
        r"(https?://|www\.|t\.me/)",
        text
    )

    if has_link:
        admin = await is_admin(
            update.effective_user.id,
            update.effective_chat.id
        )

        if not admin:
            try:
                await update.message.delete()

                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="⛔️ يمنع إرسال الروابط بدون إذن من الإشراف"
                )

            except:
                pass

# =========================
# الأزرار
# =========================

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    uid = query.from_user.id
    name = query.from_user.full_name
    data = query.data
    chat_id = query.message.chat.id

    admin = await is_admin(uid, chat_id)

    # حذف الاسم
    if data == "remove":
        cursor.execute(
            "DELETE FROM students WHERE user_id=?",
            (uid,)
        )

    # قفل / فتح التسجيل
    elif data == "toggle":

        if not admin:
            await query.answer(
                "❌ ليس لديك صلاحية",
                show_alert=True
            )
            return

        new_value = "false" if is_locked() else "true"

        cursor.execute(
            "UPDATE settings SET value=? WHERE key='locked'",
            (new_value,)
        )

    # تصفير القائمة
    elif data == "clear":

        if not admin:
            await query.answer(
                "❌ ليس لديك صلاحية",
                show_alert=True
            )
            return

        cursor.execute("DELETE FROM students")

    # تسجيل الحالات
    elif data in ["register", "read", "listen", "excuse"]:

        if is_locked() and not admin:
            await query.answer(
                "🔒 التسجيل مغلق حالياً",
                show_alert=True
            )
            return

        cursor.execute("""
        INSERT OR REPLACE INTO students
        (user_id, name, status)
        VALUES (?, ?, ?)
        """, (uid, name, data))

    conn.commit()

    await query.edit_message_text(
        text=get_status_text(),
        reply_markup=await get_keyboard(update)
    )

# =========================
# ربط المعالجات
# =========================

application.add_handler(CommandHandler("start", start))

application.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        link_filter
    )
)

application.add_handler(
    CallbackQueryHandler(handle_buttons)
)

# =========================
# الويب هوك
# =========================

@app.route("/")
def home():
    return "Bot is running ✅"


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(
        request.get_json(force=True),
        application.bot
    )

    asyncio.run(application.process_update(update))

    return "ok", 200

# =========================
# تشغيل البوت
# =========================

async def setup():
    await application.initialize()
    await application.start()

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(setup())
    loop.run_forever()

if __name__ == "__main__":

    threading.Thread(target=run_bot).start()

    app.run(
        host="0.0.0.0",
        port=PORT
    )
