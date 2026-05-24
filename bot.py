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
conn.commit()

# دالة التحقق مما إذا كان المستخدم مشرفاً
async def is_user_admin(update, context):
    user_id = update.callback_query.from_user.id
    chat_id = update.callback_query.message.chat.id
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        return any(admin.user.id == user_id for admin in admins)
    except:
        return False

def get_status_text():
    cursor.execute("SELECT name, status FROM students")
    data = cursor.fetchall()
    date = datetime.now().strftime('%Y-%m-%d')
    text = f"خادم القرآن الرقمي\n📋 قائمة تسجيل الأدوار\n📅 {date}\n\n"
    
    cats = {"register": "✍️ المسجلات", "read": "✅ قرأت", "listen": "🎧 مستمعات", "excuse": "⛔️ معتذرات"}
    for key, title in cats.items():
        text += f"{title}:\n"
        names = [n for n, s in data if s == key]
        text += "\n".join([f"• {n}" for n in names]) if names else "لا يوجد"
        text += "\n\n"
    text += "خذ الكتاب بقوة، واجعله من أولويات يومك، واقرأ تفسيره واعمل به، وأنت الرابح"
    return text

# دالة بناء الأزرار (تستقبل context للتحقق من المشرف)
async def get_keyboard(update, context):
    kb = [
        [InlineKeyboardButton("✍ سجل إسمي", callback_data="register"), InlineKeyboardButton("✅ قرأت", callback_data="read")],
        [InlineKeyboardButton("🎧 مستمعات", callback_data="listen"), InlineKeyboardButton("⛔️ معتذرات", callback_data="excuse")],
        [InlineKeyboardButton("🚫 محظورات", callback_data="ban_list"), InlineKeyboardButton("❌ إحذف إسمي", callback_data="remove")]
    ]
    
    # تحقق تلقائي من صلاحية المشرف
    if await is_user_admin(update, context):
        kb.append([InlineKeyboardButton("🔒 قفل/فتح", callback_data="toggle"), InlineKeyboardButton("🗑 تصفير القائمة", callback_data="clear")])
    
    return InlineKeyboardMarkup(kb)

# --- الأوامر ---
async def start(update, context):
    # عند استخدام الأمر /start في البداية نعتبر المستخدم العادي هو الظاهر
    await update.message.reply_text(get_status_text(), reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("✍ سجل إسمي", callback_data="register"), InlineKeyboardButton("✅ قرأت", callback_data="read")],
        [InlineKeyboardButton("🎧 مستمعات", callback_data="listen"), InlineKeyboardButton("⛔️ معتذرات", callback_data="excuse")],
        [InlineKeyboardButton("🚫 محظورات", callback_data="ban_list"), InlineKeyboardButton("❌ إحذف إسمي", callback_data="remove")]
    ]))

async def buttons(update, context):
    query = update.callback_query
    await query.answer()
    uid, name, data = query.from_user.id, query.from_user.full_name, query.data
    
    if data in ["register", "read", "listen", "excuse"]:
        cursor.execute("INSERT OR REPLACE INTO students VALUES (?, ?, ?)", (uid, name, data))
    elif data == "remove":
        cursor.execute("DELETE FROM students WHERE user_id=?", (uid,))
    elif data == "clear" and await is_user_admin(update, context):
        cursor.execute("DELETE FROM students")
    conn.commit()
    
    await query.edit_message_text(get_status_text(), reply_markup=await get_keyboard(update, context))

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(buttons))

@app.route('/webhook', methods=['POST'])
def webhook():
    json_data = request.get_json(force=True)
    update = Update.de_json(json_data, application.bot)
    asyncio.run(application.process_update(update))
    return 'ok', 200

async def init_bot():
    await application.initialize()
    await application.start()

if __name__ == '__main__':
    asyncio.run(init_bot())
    app.run(host='0.0.0.0', port=PORT)
