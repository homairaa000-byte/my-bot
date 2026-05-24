import os
import sqlite3
from datetime import datetime
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# =========================
# الإعدادات
# =========================
TOKEN = os.environ.get("BOT_TOKEN")
BASE_URL = os.environ.get("BASE_URL")
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

def set_student(user_id, name, status):
    cursor.execute(
        "INSERT OR REPLACE INTO students VALUES (?, ?, ?)",
        (user_id, name, status)
    )
    conn.commit()

def remove_student(user_id):
    cursor.execute("DELETE FROM students WHERE user_id=?", (user_id,))
    conn.commit()

def clear_all():
    cursor.execute("DELETE FROM students")
    conn.commit()

def get_all():
    cursor.execute("SELECT name, status FROM students")
    return cursor.fetchall()

# =========================
# إعدادات البوت
# =========================
registration_open = True

ADMIN_IDS = list(map(int, os.environ.get("ADMIN_IDS", "").split(","))) \
    if os.environ.get("ADMIN_IDS") else []

# =========================
# واجهة الحالة
# =========================
def get_status():
    date_now = datetime.now().strftime("%Y-%m-%d")
    data = get_all()

    text = "🤖 بوت الأكاديمية\n"
    text += f"📅 {date_now}\n\n"
    text += f"🔒 التسجيل: {'مفتوح ✅' if registration_open else 'مغلق ⛔'}\n"
    text += "━━━━━━━━━━━━━━\n"

    categories = {
        "read": "📘 قرأت",
        "listen": "🎧 مستمعة",
        "excuse": "🚫 معتذرة"
    }

    for key, title in categories.items():
        text += f"\n{title}:\n"
        items = [n for n, s in data if s == key]
        text += "\n".join([f"• {i}" for i in items]) if items else "لا يوجد\n"

    return text

# =========================
# /start
# =========================
async def start(update, context):
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📘 قرأت", callback_data="read"),
            InlineKeyboardButton("🎧 مستمعة", callback_data="listen")
        ],
        [
            InlineKeyboardButton("🚫 معتذرة", callback_data="excuse"),
            InlineKeyboardButton("❌ حذف اسمي", callback_data="remove")
        ],
        [
            InlineKeyboardButton("🔒 قفل/فتح", callback_data="toggle"),
            InlineKeyboardButton("🧹 تصفير", callback_data="clear")
        ]
    ])

    await update.message.reply_text(get_status(), reply_markup=kb)

# =========================
# الأزرار
# =========================
async def buttons(update, context):
    global registration_open

    query = update.callback_query
    await query.answer()

    uid = query.from_user.id
    name = query.from_user.full_name
    data = query.data

    if data in ["read", "listen", "excuse"]:
        if registration_open:
            set_student(uid, name, data)
        else:
            await query.answer("التسجيل مغلق ⛔", show_alert=True)
            return

    elif data == "remove":
        remove_student(uid)

    elif data == "toggle":
        if uid in ADMIN_IDS:
            registration_open = not registration_open
        else:
            await query.answer("ليس لديك صلاحية", show_alert=True)
            return

    elif data == "clear":
        if uid in ADMIN_IDS:
            clear_all()
        else:
            await query.answer("ليس لديك صلاحية", show_alert=True)
            return

    await query.edit_message_text(
        get_status(),
        reply_markup=query.message.reply_markup
    )

# =========================
# handlers
# =========================
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(buttons))

# =========================
# webhook route
# =========================
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "ok"

# =========================
# تشغيل السيرفر
# =========================
if __name__ == "__main__":
    # مهم جدًا
    application.initialize()

    # webhook
    application.bot.set_webhook(
        url=f"{BASE_URL}/{TOKEN}"
    )

    # flask
    app.run(host="0.0.0.0", port=PORT)
