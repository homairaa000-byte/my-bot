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

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# --- قاعدة البيانات ---
conn = sqlite3.connect("students.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS students (user_id INTEGER PRIMARY KEY, name TEXT, status TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS banned (user_id INTEGER PRIMARY KEY)") # جدول المحظورات
conn.commit()

def is_banned(user_id):
    cursor.execute("SELECT 1 FROM banned WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

# --- معالجة الأوامر ---
async def start(update, context):
    if is_banned(update.message.from_user.id):
        await update.message.reply_text("عذراً، أنت محظور من استخدام هذا البوت.")
        return
    await update.message.reply_text("أهلاً بك في خادم القرآن.")

async def ban_user(update, context):
    # مثال لأمر الحظر: /ban 123456
    if context.args:
        target_id = int(context.args[0])
        cursor.execute("INSERT OR IGNORE INTO banned VALUES (?)", (target_id,))
        conn.commit()
        await update.message.reply_text(f"تم حظر المستخدم {target_id}")

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("ban", ban_user)) # أمر الحظر للإدارة

# --- دالة الويب هوك ---
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    try:
        json_data = request.get_json(force=True)
        # التأكد أن المستخدم غير محظور قبل المعالجة
        user_id = json_data.get('message', {}).get('from', {}).get('id')
        if user_id and is_banned(user_id):
            return 'banned', 200
            
        update = Update.de_json(json_data, application.bot)
        asyncio.run(application.process_update(update))
        return 'ok', 200
    except Exception as e:
        traceback.print_exc()
        return 'error', 500

async def init_bot():
    await application.initialize()
    await application.start()

if __name__ == '__main__':
    asyncio.run(init_bot())
    app.run(host='0.0.0.0', port=PORT)
