import os
import sqlite3
import asyncio
import traceback
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# --- الإعدادات ---
TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))
ADMIN_IDS = [int(id.strip()) for id in os.environ.get("ADMIN_IDS", "").split(",") if id.strip()]

app = Flask(__name__)

# --- تهيئة البوت ---
application = Application.builder().token(TOKEN).build()

# --- قاعدة البيانات ---
conn = sqlite3.connect("students.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS students (user_id INTEGER PRIMARY KEY, name TEXT, status TEXT)")
conn.commit()

def set_student(user_id, name, status):
    cursor.execute("INSERT OR REPLACE INTO students VALUES (?, ?, ?)", (user_id, name, status))
    conn.commit()

def remove_student(user_id):
    cursor.execute("DELETE FROM students WHERE user_id=?", (user_id,))
    conn.commit()

def get_all():
    cursor.execute("SELECT name, status FROM students")
    return cursor.fetchall()

# --- واجهة البوت ---
def get_status():
    data = get_all()
    text = "السلام عليكم ورحمة الله وبركاته\n\n🤖 خادم القرآن الذكي\n"
    categories = {"read": "✅ قرأت", "listen": "🎧 مستمعات", "excuse": "⛔️ معتذرات"}
    for key, title in categories.items():
        text += f"\n{title}:\n"
        items = [n for n, s in data if s == key]
        text += "\n".join([f"• {i}" for i in items]) if items else "لا يوجد"
        text += "\n"
    return text

def keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ قرأت", callback_data="read"), InlineKeyboardButton("🎧 مستمعات", callback_data="listen")],
        [InlineKeyboardButton("⛔️ معتذرات", callback_data="excuse"), InlineKeyboardButton("❌ إحذف إسمي", callback_data="remove")]
    ])

async def start(update, context):
    await update.message.reply_text(get_status(), reply_markup=keyboard())

async def buttons(update, context):
    query = update.callback_query
    await query.answer()
    uid, name, data = query.from_user.id, query.from_user.full_name, query.data
    if data in ["read", "listen", "excuse"]: set_student(uid, name, data)
    elif data == "remove": remove_student(uid)
    await query.edit_message_text(text=get_status(), reply_markup=keyboard())

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(buttons))

# --- دالة الويب هوك المصححة ---
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    try:
        # تأكد من تهيئة التطبيق (حل المشكلة)
        if not application.initialized:
            asyncio.run(application.initialize())
            
        json_data = request.get_json(force=True)
        update = Update.de_json(json_data, application.bot)
        asyncio.run(application.process_update(update))
        return 'ok', 200
    except Exception as e:
        print("!!! ERROR DETECTED !!!")
        traceback.print_exc()
        return 'error', 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
