import os
import sqlite3
import asyncio
from flask import Flask, request
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# --- الإعدادات ---
TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))
# تأكدي أن ADMIN_IDS في Render مكتوبة كأرقام مفصولة بفاصلة مثل: 12345,67890
ADMIN_IDS = [int(id.strip()) for id in os.environ.get("ADMIN_IDS", "").split(",") if id.strip()]

app = Flask(__name__)
# إنشاء التطبيق
application = Application.builder().token(TOKEN).build()

# --- قاعدة البيانات ---
conn = sqlite3.connect("students.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS students (user_id INTEGER PRIMARY KEY, name TEXT, status TEXT)")
conn.commit()

# --- الوظائف ---
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

def get_status():
    data = get_all()
    text = f"🤖 بوت الأكاديمية\n📅 {datetime.now().strftime('%Y-%m-%d')}\n\n🔒 التسجيل: {'مفتوح ✅' if registration_open else 'مغلق ⛔'}\n"
    categories = {"read": "📘 قرأت", "listen": "🎧 مستمعة", "excuse": "🚫 معتذرة"}
    for key, title in categories.items():
        text += f"\n{title}:\n"
        items = [n for n, s in data if s == key]
        text += "\n".join([f"• {i}" for i in items]) if items else "لا يوجد"
        text += "\n"
    return text

def keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ قرأت", callback_data="read"), InlineKeyboardButton("🎧 مستمعة", callback_data="listen")],
        [InlineKeyboardButton("🚫 معتذرة", callback_data="excuse"), InlineKeyboardButton("❌ حذف اسمي", callback_data="remove")],
        [InlineKeyboardButton("🔒 قفل/فتح", callback_data="toggle"), InlineKeyboardButton("🧹 تصفير", callback_data="clear")],
    ])

# --- الأوامر ---
async def start(update, context):
    await update.message.reply_text(get_status(), reply_markup=keyboard())

async def buttons(update, context):
    global registration_open
    query = update.callback_query
    await query.answer()
    uid, name, data = query.from_user.id, query.from_user.full_name, query.data
    
    if data in ["read", "listen", "excuse"]:
        if registration_open:
            set_student(uid, name, data)
        else:
            await query.answer("التسجيل مغلق حالياً!", show_alert=True)
    elif data == "remove":
        remove_student(uid)
    elif data in ["toggle", "clear"]:
        if uid in ADMIN_IDS:
            if data == "toggle": registration_open = not registration_open
            if data == "clear": clear_all()
        else:
            await query.answer("هذا الزر للمشرفين فقط!", show_alert=True)
    
    await query.edit_message_text(text=get_status(), reply_markup=keyboard())

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(buttons))

# --- الـ Webhook (الجسر) ---
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run(application.process_update(update))
    return 'ok', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
