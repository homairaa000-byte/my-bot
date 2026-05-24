import os
import sqlite3
import asyncio
import re
import threading
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)
# إنشاء تطبيق البوت
application = Application.builder().token(TOKEN).build()

# تهيئة قاعدة البيانات
conn = sqlite3.connect("students.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS students (user_id INTEGER PRIMARY KEY, name TEXT, status TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS banned (user_id INTEGER PRIMARY KEY, name TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
cursor.execute("INSERT OR IGNORE INTO settings VALUES ('locked', 'false')")
conn.commit()

# --- المنطق الأساسي ---
async def is_admin(user_id, chat_id):
    try:
        admins = await application.bot.get_chat_administrators(chat_id)
        return any(admin.user.id == user_id for admin in admins)
    except: return False

def get_status_text():
    cursor.execute("SELECT name, status FROM students")
    data = cursor.fetchall()
    cursor.execute("SELECT name FROM banned")
    banned_list = [row[0] for row in cursor.fetchall()]
    
    text = "السلام عليكم ورحمة الله وبركاته\n\nخادم القرآن الرقمي\n📋 قائمة تسجيل الأدوار\n\n"
    cats = {"register": "✍️ المسجلات", "read": "✅ قرأت", "listen": "🎧 مستمعات", "excuse": "⛔️ معتذرات"}
    
    for key, title in cats.items():
        text += f"{title}:\n"
        names = [f"• {n} ✅" if key == "register" and s == "read" else f"• {n}" for n, s in data if s == key]
        text += "\n".join(names) if names else "لا يوجد"
        text += "\n\n"
    
    text += f"🚫 المحظورات:\n" + ("\n".join([f"• {n}" for n in banned_list]) or "لا يوجد")
    text += "\n\nخذ الكتاب بقوة، واجعله من أولويات يومك، واقرأ تفسيره واعمل به، وأنت الرابح\n\nالسلام عليكم ورحمة الله وبركاته"
    return text

async def get_keyboard(update):
    kb = [
        [InlineKeyboardButton("✍ سجل إسمي", callback_data="register"), InlineKeyboardButton("❌ إحذف إسمي", callback_data="remove")],
        [InlineKeyboardButton("✅ قرأت", callback_data="read"), InlineKeyboardButton("🎧 مستمعات", callback_data="listen")],
        [InlineKeyboardButton("⛔️ معتذرات", callback_data="excuse")]
    ]
    if await is_admin(update.effective_user.id, update.effective_chat.id):
        locked = cursor.execute("SELECT value FROM settings WHERE key='locked'").fetchone()[0] == 'true'
        status = "🔓 فتح التسجيل" if locked else "🔒 قفل التسجيل"
        kb.append([InlineKeyboardButton(status, callback_data="toggle"), InlineKeyboardButton("🗑 تصفير القائمة", callback_data="clear")])
    return InlineKeyboardMarkup(kb)

# --- معالجات البوت ---
async def start(update, context):
    await update.message.reply_text(get_status_text(), reply_markup=await get_keyboard(update))

async def link_filter(update, context):
    if not await is_admin(update.effective_user.id, update.effective_chat.id) and re.search(r'http[s]?://|www\.|t\.me/', update.message.text or ""):
        await update.message.delete()
        await update.message.reply_text("⛔️⛔️⛔️ إرسال روابط من دون الرجوع للإشراف يعرضك للحذف")

async def handle_buttons(update, context):
    query = update.callback_query
    await query.answer()
    uid, name, data = query.from_user.id, query.from_user.full_name, query.data
    
    if data == "toggle":
        curr = cursor.execute("SELECT value FROM settings WHERE key='locked'").fetchone()[0]
        cursor.execute("UPDATE settings SET value=? WHERE key='locked'", ('false' if curr == 'true' else 'true',))
    elif data == "clear" and await is_admin(uid, query.message.chat.id):
        cursor.execute("DELETE FROM students")
    elif data == "remove":
        cursor.execute("DELETE FROM students WHERE user_id=?", (uid,))
    elif data in ["register", "read", "listen", "excuse"]:
        if cursor.execute("SELECT value FROM settings WHERE key='locked'").fetchone()[0] == 'true' and not await is_admin(uid, query.message.chat.id):
            await query.answer("التسجيل مغلق حالياً!", show_alert=True)
            return
        cursor.execute("INSERT OR REPLACE INTO students VALUES (?, ?, ?)", (uid, name, data))
    
    conn.commit()
    await query.edit_message_text(get_status_text(), reply_markup=await get_keyboard(update))

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, link_filter))
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(handle_buttons))

# --- الويب هوك (خارج asyncio.run) ---
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.create_task(application.process_update(update))
    return 'ok', 200

if __name__ == '__main__':
    application.initialize()
    application.start()
    app.run(host='0.0.0.0', port=PORT)
