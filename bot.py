import os
import sqlite3
import asyncio
import re
from datetime import datetime
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
application = Application.builder().token(TOKEN).event_loop(loop).build()

conn = sqlite3.connect("students.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS students (user_id INTEGER PRIMARY KEY, name TEXT, status TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS banned (user_id INTEGER PRIMARY KEY, name TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
cursor.execute("INSERT OR IGNORE INTO settings VALUES ('locked', 'false')")
conn.commit()

async def is_admin(update, context):
    try:
        user_id = update.effective_user.id
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
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

async def get_keyboard(update, context):
    kb = [
        [InlineKeyboardButton("✍ سجل إسمي", callback_data="register"), InlineKeyboardButton("❌ إحذف إسمي", callback_data="remove")],
        [InlineKeyboardButton("✅ قرأت", callback_data="read"), InlineKeyboardButton("🎧 مستمعات", callback_data="listen")],
        [InlineKeyboardButton("⛔️ معتذرات", callback_data="excuse")]
    ]
    if await is_admin(update, context):
        status = "🔓 فتح" if cursor.execute("SELECT value FROM settings WHERE key='locked'").fetchone()[0] == 'true' else "🔒 قفل"
        kb.append([InlineKeyboardButton(status, callback_data="toggle"), InlineKeyboardButton("🗑 تصفير القائمة", callback_data="clear")])
    return InlineKeyboardMarkup(kb)

# --- فلتر الروابط ---
async def link_filter(update, context):
    if not await is_admin(update, context):
        if re.search(r'http[s]?://|www\.|t\.me/', update.message.text or ""):
            await update.message.delete()
            await update.message.reply_text("⛔️⛔️⛔️ إرسال روابط من دون الرجوع للإشراف يعرضك للحذف")

# --- الأزرار ---
async def handle_buttons(update, context):
    query = update.callback_query
    uid, name, data = query.from_user.id, query.from_user.full_name, query.data
    
    if data == "toggle":
        new_val = 'false' if cursor.execute("SELECT value FROM settings WHERE key='locked'").fetchone()[0] == 'true' else 'true'
        cursor.execute("UPDATE settings SET value=? WHERE key='locked'", (new_val,))
    elif data == "clear" and await is_admin(update, context):
        cursor.execute("DELETE FROM students")
    elif data == "remove":
        cursor.execute("DELETE FROM students WHERE user_id=?", (uid,))
    elif data in ["register", "read", "listen", "excuse"]:
        # منع التسجيل إذا كان مغلقاً
        if cursor.execute("SELECT value FROM settings WHERE key='locked'").fetchone()[0] == 'true' and not await is_admin(update, context):
            await query.answer("التسجيل مغلق حالياً!", show_alert=True)
            return
        cursor.execute("INSERT OR REPLACE INTO students VALUES (?, ?, ?)", (uid, name, data))
    
    conn.commit()
    await query.answer()
    await query.edit_message_text(get_status_text(), reply_markup=await get_keyboard(update, context))

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, link_filter))
application.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text(get_status_text(), reply_markup=loop.run_until_complete(get_keyboard(u, c)))))
application.add_handler(CallbackQueryHandler(handle_buttons))

@app.route('/webhook', methods=['POST'])
def webhook():
    asyncio.run_coroutine_threadsafe(application.process_update(Update.de_json(request.get_json(force=True), application.bot)), loop)
    return 'ok', 200

if __name__ == '__main__':
    loop.run_until_complete(application.initialize())
    loop.run_until_complete(application.start())
    app.run(host='0.0.0.0', port=PORT)
