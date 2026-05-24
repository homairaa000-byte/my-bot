import os
import sqlite3
import asyncio
from datetime import datetime
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# قاعدة البيانات
conn = sqlite3.connect("students.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS students (user_id INTEGER PRIMARY KEY, name TEXT, status TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS banned (user_id INTEGER PRIMARY KEY, name TEXT)")
conn.commit()

async def is_admin(update, context):
    try:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        admins = await context.bot.get_chat_administrators(chat_id)
        return any(admin.user.id == user_id for admin in admins)
    except: return False

def get_status_text():
    cursor.execute("SELECT name, status FROM students")
    data = cursor.fetchall()
    cursor.execute("SELECT name FROM banned")
    banned_list = [row[0] for row in cursor.fetchall()]
    
    date = datetime.now().strftime('%Y-%m-%d')
    text = f"خادم القرآن الرقمي\n📋 قائمة تسجيل الأدوار\n📅 {date}\n\n"
    
    text += "✍️ المسجلات:\n"
    for n, s in data:
        check = " ✅" if s == "read" else ""
        text += f"• {n}{check}\n"
    
    text += f"\n🎧 مستمعات:\n" + "\n".join([f"• {n}" for n, s in data if s == "listen"])
    text += f"\n\n⛔️ معتذرات:\n" + "\n".join([f"• {n}" for n, s in data if s == "excuse"])
    text += f"\n\n🚫 المحظورات:\n" + "\n".join([f"• {n}" for n in banned_list])
    
    text += "\n\nخذ الكتاب بقوة، واجعله من أولويات يومك، واقرأ تفسيره واعمل به، وأنت الرابح"
    return text

async def get_keyboard(update, context):
    kb = [
        [InlineKeyboardButton("✍ سجل إسمي", callback_data="register"), InlineKeyboardButton("✅ قرأت", callback_data="read")],
        [InlineKeyboardButton("🎧 مستمعات", callback_data="listen"), InlineKeyboardButton("⛔️ معتذرات", callback_data="excuse")],
        [InlineKeyboardButton("❌ إحذف إسمي", callback_data="remove")]
    ]
    if await is_admin(update, context):
        kb.append([InlineKeyboardButton("🔒 قفل/فتح", callback_data="toggle"), InlineKeyboardButton("🗑 تصفير القائمة", callback_data="clear")])
    return InlineKeyboardMarkup(kb)

async def start(update, context):
    await update.message.reply_text(get_status_text(), reply_markup=await get_keyboard(update, context))

async def handle_buttons(update, context):
    query = update.callback_query
    await query.answer()
    uid, name, data = query.from_user.id, query.from_user.full_name, query.data
    
    if data in ["register", "read", "listen", "excuse"]:
        cursor.execute("INSERT OR REPLACE INTO students VALUES (?, ?, ?)", (uid, name, data))
    elif data == "remove":
        cursor.execute("DELETE FROM students WHERE user_id=?", (uid,))
    elif data == "clear" and await is_admin(update, context):
        cursor.execute("DELETE FROM students")
    conn.commit()
    await query.edit_message_text(get_status_text(), reply_markup=await get_keyboard(update, context))

async def ban_user(update, context):
    if await is_admin(update, context) and update.message.reply_to_message:
        t = update.message.reply_to_message.from_user
        cursor.execute("INSERT OR IGNORE INTO banned VALUES (?, ?)", (t.id, t.full_name))
        conn.commit()
        await update.message.reply_text(f"تم حظر {t.full_name}")

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("ban", ban_user))
application.add_handler(CallbackQueryHandler(handle_buttons))

@app.route('/webhook', methods=['POST'])
def webhook():
    asyncio.run(application.process_update(Update.de_json(request.get_json(force=True), application.bot)))
    return 'ok', 200

if __name__ == '__main__':
    asyncio.run(application.initialize())
    asyncio.run(application.start())
    app.run(host='0.0.0.0', port=PORT)
