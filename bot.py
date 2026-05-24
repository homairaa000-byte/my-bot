import os
import sqlite3
import asyncio
import traceback
from datetime import datetime
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

# --- الأزرار ---
def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍ سجل إسمي", callback_data="register"), InlineKeyboardButton("✅ قرأت", callback_data="read")],
        [InlineKeyboardButton("🎧 مستمعات", callback_data="listen"), InlineKeyboardButton("⛔️ معتذرات", callback_data="excuse")],
        [InlineKeyboardButton("🚫 محظورات", callback_data="ban_list"), InlineKeyboardButton("❌ إحذف إسمي", callback_data="remove")]
    ])

def get_header():
    makkah_time = datetime.now().strftime('%Y-%m-%d')
    return f"السلام عليكم ورحمة الله وبركاته\n\n🤖 خادم القرآن الرقمي\n📅 {makkah_time}\n"

def get_footer():
    return "\nخذ الكتاب بقوة، واجعله من أولويات يومك، واقرأ تفسيره واعمل به، وأنت الرابح"

# --- الأوامر ---
async def start(update, context):
    text = f"{get_header()}\nأهلاً بكِ في خادم القرآن الرقمي. اختاري إجراءً من القائمة:{get_footer()}"
    await update.message.reply_text(text, reply_markup=get_main_keyboard())

async def buttons(update, context):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    name = query.from_user.full_name
    data = query.data
    
    cursor.execute("SELECT 1 FROM banned WHERE user_id=?", (uid,))
    if cursor.fetchone():
        await query.answer("عذراً، أنتِ محظورة من استخدام البوت.", show_alert=True)
        return

    if data in ["register", "read", "listen", "excuse"]:
        cursor.execute("INSERT OR REPLACE INTO students VALUES (?, ?, ?)", (uid, name, data))
        conn.commit()
        await query.edit_message_text(f"{get_header()}\nتم تحديث حالتكِ إلى: {data}{get_footer()}", reply_markup=get_main_keyboard())
    elif data == "remove":
        cursor.execute("DELETE FROM students WHERE user_id=?", (uid,))
        conn.commit()
        await query.edit_message_text(f"{get_header()}\nتم حذف اسمكِ من القائمة.{get_footer()}", reply_markup=get_main_keyboard())
    elif data == "ban_list":
        await query.answer("هذا الزر للمشرفات فقط. استخدمي الأمر /ban للرد على رسالة الطالبة للحظر.", show_alert=True)

# أمر الحظر أصبح بالإنجليزية الآن
async def ban_command(update, context):
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
        cursor.execute("INSERT OR IGNORE INTO banned VALUES (?)", (target_id,))
        conn.commit()
        await update.message.reply_text(f"تم حظر الطالبة بنجاح.")

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("ban", ban_command))
application.add_handler(CallbackQueryHandler(buttons))

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    try:
        json_data = request.get_json(force=True)
        update = Update.de_json(json_data, application.bot)
        asyncio.run(application.process_update(update))
        return 'ok', 200
    except Exception:
        return 'error', 500

async def init_bot():
    await application.initialize()
    await application.start()

if __name__ == '__main__':
    asyncio.run(init_bot())
    app.run(host='0.0.0.0', port=PORT)
