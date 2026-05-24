import os
import sqlite3
import asyncio
import traceback
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# --- قاعدة البيانات ---
conn = sqlite3.connect("students.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS students (user_id INTEGER PRIMARY KEY, name TEXT, status TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS banned (user_id INTEGER PRIMARY KEY)")
conn.commit()

# --- الأزرار بالتنسيق الجديد ---
def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍ سجل إسمي", callback_data="register"), InlineKeyboardButton("✅ قرأت", callback_data="read")],
        [InlineKeyboardButton("🎧 مستمعات", callback_data="listen"), InlineKeyboardButton("⛔️ معتذرات", callback_data="excuse")],
        [InlineKeyboardButton("🚫 محظورات", callback_data="ban_list"), InlineKeyboardButton("❌ إحذف إسمي", callback_data="remove")]
    ])

# --- معالجة الأوامر ---
async def start(update, context):
    await update.message.reply_text("أهلاً بك في خادم القرآن. اختاري إجراءً من القائمة:", reply_markup=get_main_keyboard())

async def buttons(update, context):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    name = query.from_user.full_name
    data = query.data
    
    if data in ["register", "read", "listen", "excuse"]:
        cursor.execute("INSERT OR REPLACE INTO students VALUES (?, ?, ?)", (uid, name, data))
        conn.commit()
        await query.edit_message_text(f"تم تحديث حالتك إلى: {data}", reply_markup=get_main_keyboard())
    elif data == "remove":
        cursor.execute("DELETE FROM students WHERE user_id=?", (uid,))
        conn.commit()
        await query.edit_message_text("تم حذف اسمك من القائمة.", reply_markup=get_main_keyboard())
    elif data == "ban_list":
        await query.answer("قائمة المحظورات (فقط للإدارة)", show_alert=True)

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(buttons))

# --- الويب هوك ---
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    try:
        json_data = request.get_json(force=True)
        update = Update.de_json(json_data, application.bot)
        asyncio.run(application.process_update(update))
        return 'ok', 200
    except Exception:
        traceback.print_exc()
        return 'error', 500

async def init_bot():
    await application.initialize()
    await application.start()

if __name__ == '__main__':
    asyncio.run(init_bot())
    app.run(host='0.0.0.0', port=PORT)
