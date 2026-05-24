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
ADMIN_IDS = [int(id.strip()) for id in os.environ.get("ADMIN_IDS", "").split(",") if id.strip()]

app = Flask(__name__)

# تهيئة التطبيق خارج الدالة لضمان استقراره
application = Application.builder().token(TOKEN).build()

# --- قاعدة البيانات ---
conn = sqlite3.connect("students.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS students (user_id INTEGER PRIMARY KEY, name TEXT, status TEXT)")
conn.commit()

# --- دوال المنطق ---
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
    text = "السلام عليكم ورحمة الله وبركاته\n\n"
    text += f"🤖 خادم القرآن الذكي\n📅 {datetime.now().strftime('%Y-%m-%d')}\n\n🔒 التسجيل: {'مفتوح ✅' if registration_open else 'مغلق ⛔'}\n"
    
    categories = {"read": "✅ قرأت", "listen": "🎧 مستمعات", "excuse": "⛔️ معتذرات"}
    for key, title in categories.items():
        text += f"\n{title}:\n"
        items = [n for n, s in data if s == key]
        text += "\n".join([f"• {i}" for i in items]) if items else "لا يوجد"
        text += "\n"
    
    text += "\n--------------------------\n"
    text += "خذ الكتاب بقوة، واجعله من أولويات يومك، واقرأ تفسيره واعمل به، وأنت الرابح"
    return text

def keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍ سجل إسمي", callback_data="register"), InlineKeyboardButton("✅ قرأت", callback_data="read")],
        [InlineKeyboardButton("🎧 مستمعات", callback_data="listen"), InlineKeyboardButton("⛔️ معتذرات", callback_data="excuse")],
        [InlineKeyboardButton("🚫 محظورات", callback_data="ban_list"), InlineKeyboardButton("❌ إحذف إسمي", callback_data="remove")],
        [InlineKeyboardButton("🔒 قفل/فتح التسجيل", callback_data="toggle"), InlineKeyboardButton("🧹 تصفير القائمة", callback_data="clear")]
    ])

# --- معالجة الأوامر ---
async def start(update, context):
    await update.message.reply_text(get_status(), reply_markup=keyboard())

async def buttons(update, context):
    global registration_open
    query = update.callback_query
    await query.answer()
    uid, name, data = query.from_user.id, query.from_user.full_name, query.data
    
    if data == "register" and registration_open:
        set_student(uid, name, "registered")
        await query.answer("تم تسجيل اسمك!")
    elif data in ["read", "listen", "excuse"] and registration_open:
        set_student(uid, name, data)
    elif data == "remove":
        remove_student(uid)
    elif data in ["toggle", "clear"] and uid in ADMIN_IDS:
        if data == "toggle": registration_open = not registration_open
        if data == "clear": clear_all()
    else:
        await query.answer("غير متاح أو ليست لديك صلاحية!", show_alert=True)
    
    await query.edit_message_text(text=get_status(), reply_markup=keyboard())

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(buttons))

# --- دالة الويب هوك المعدلة (تجنب خطأ 500) ---
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    try:
        json_data = request.get_json(force=True)
        update = Update.de_json(json_data, application.bot)
        # تشغيل التحديث بشكل غير متزامن داخل حلقة أحداث مخصصة
        asyncio.run(application.process_update(update))
        return 'ok', 200
    except Exception as e:
        print(f"Error: {e}")
        return 'internal server error', 500

if __name__ == '__main__':
    # تهيئة الـ Handlers قبل تشغيل التطبيق
    app.run(host='0.0.0.0', port=PORT)
