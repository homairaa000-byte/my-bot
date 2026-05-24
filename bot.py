import os
import sqlite3
import asyncio
import traceback
from flask import Flask, request
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# --- الإعدادات ---
TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))
ADMIN_IDS = [int(id.strip()) for id in os.environ.get("ADMIN_IDS", "").split(",") if id.strip()]

app = Flask(__name__)

# تهيئة التطبيق
application = Application.builder().token(TOKEN).build()

# --- قاعدة البيانات ---
# استخدام check_same_thread=False ضروري لـ SQLite في Flask
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

def clear_all():
    cursor.execute("DELETE FROM students")
    conn.commit()

def get_all():
    cursor.execute("SELECT name, status FROM students")
    return cursor.fetchall()

registration_open = True

# --- واجهة البوت ---
def get_status():
    data = get_all()
    text = "السلام عليكم ورحمة الله وبركاته\n\n🤖 خادم القرآن الذكي\n\n"
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

# --- معالجة الأوامر ---
async def start(update, context):
    await update.message.reply_text(get_status(), reply_markup=keyboard())

async def buttons(update, context):
    query = update.callback_query
    await query.answer()
    uid, name, data = query.from_user.id, query.from_user.full_name, query.data
    
    if data in ["read", "listen", "excuse"]:
        set_student(uid, name, data)
    elif data == "remove":
        remove_student(uid)
    
    await query.edit_message_text(text=get_status(), reply_markup=keyboard())

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(buttons))

# --- دالة الويب هوك مع كشف الأخطاء ---
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    try:
        json_data = request.get_json(force=True)
        update = Update.de_json(json_data, application.bot)
        # تشغيل التحديث
        asyncio.run(application.process_update(update))
        return 'ok', 200
    except Exception as e:
        # طباعة الخطأ بالتفصيل في الـ Logs
        print("!!! ERROR DETECTED !!!")
        traceback.print_exc()
        return 'error', 500

@app.route('/', methods=['GET'])
def index():
    return "Bot is running", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
