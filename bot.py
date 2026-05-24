import os
import sqlite3
import asyncio
from datetime import datetime
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ====== الإعدادات ======
TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# ====== قاعدة البيانات ======
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
    cursor.execute("INSERT OR REPLACE INTO students VALUES (?, ?, ?)",
                   (user_id, name, status))
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

registration_open = True

# ====== التحقق من الأدمن (الأهم هنا) ======
async def is_admin(update: Update):
    member = await update.effective_chat.get_member(update.effective_user.id)
    return member.status in ["administrator", "creator"]

# ====== واجهة الحالة ======
def get_status():
    date_now = datetime.now().strftime("%Y-%m-%d")
    data = get_all()

    text = f"""🤖 بوت الأكاديمية
📅 {date_now}

🔒 التسجيل: {'مفتوح ✅' if registration_open else 'مغلق ⛔'}
-----------------------
"""

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

# ====== /start ======
async def start(update, context):
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ قرأت", callback_data="read"),
            InlineKeyboardButton("🎧 مستمعة", callback_data="listen")
        ],
        [
            InlineKeyboardButton("🚫 معتذرة", callback_data="excuse"),
            InlineKeyboardButton("❌ حذف اسمي", callback_data="remove")
        ],
        [
            InlineKeyboardButton("🔒 قفل/فتح", callback_data="toggle"),
            InlineKeyboardButton("🧹 تصفير", callback_data="clear")
        ],
    ])

    await update.message.reply_text(get_status(), reply_markup=kb)

# ====== الأزرار ======
async def buttons(update, context):
    global registration_open

    query = update.callback_query
    await query.answer()

    uid = query.from_user.id
    name = query.from_user.full_name
    data = query.data

    admin = await is_admin(update)

    if data in ["read", "listen", "excuse"] and registration_open:
        set_student(uid, name, data)

    elif data == "remove":
        remove_student(uid)

    elif data == "toggle":
        if admin:
            registration_open = not registration_open
        else:
            await query.answer("ليس لديك صلاحية", show_alert=True)

    elif data == "clear":
        if admin:
            clear_all()
        else:
            await query.answer("ليس لديك صلاحية", show_alert=True)

    await query.edit_message_text(
        text=get_status(),
        reply_markup=query.message.reply_markup
    )

# ====== Flask Webhook ======
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run(application.process_update(update))
    return "ok"

# ====== تشغيل ======
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
