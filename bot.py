import os
import logging
import asyncio
import aiosqlite
from datetime import datetime
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# 1. الإعدادات
TOKEN = os.getenv("BOT_TOKEN")
DB = "bot.db"

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# تهيئة البوت خارج Flask ليكون جاهزاً دائماً
bot_app = Application.builder().token(TOKEN).build()
bot = Bot(TOKEN)

async def get_db():
    db_conn = await aiosqlite.connect(DB)
    await db_conn.execute("CREATE TABLE IF NOT EXISTS groups (chat_id INTEGER PRIMARY KEY, locked INTEGER DEFAULT 0)")
    await db_conn.execute("CREATE TABLE IF NOT EXISTS users (chat_id INTEGER, user_id INTEGER, name TEXT, status TEXT, read_status INTEGER DEFAULT 0, PRIMARY KEY(chat_id, user_id))")
    await db_conn.commit()
    return db_conn

# 2. الدوال الأساسية (بدون تغيير)
async def get_locked(chat_id):
    conn = await get_db()
    await conn.execute("INSERT OR IGNORE INTO groups(chat_id, locked) VALUES (?,0)", (chat_id,))
    async with conn.execute("SELECT locked FROM groups WHERE chat_id=?", (chat_id,)) as cursor:
        row = await cursor.fetchone()
        return row[0] if row else 0

async def build(chat_id):
    conn = await get_db()
    locked = await get_locked(chat_id)
    async with conn.execute("SELECT name,status,read_status FROM users WHERE chat_id=?", (chat_id,)) as cursor:
        data = await cursor.fetchall()
    
    status_text = "🔒 التسجيل مغلق" if locked else "🔓 التسجيل مفتوح"
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    def section(status):
        result = [f"{name}{' ✅' if read_status == 1 else ''}" for name, st, read_status in data if st == status]
        return "\n".join(f"{i+1}- {x}" for i, x in enumerate(result)) if result else "لا يوجد"
    
    return (
        "السلام عليكم ورحمة الله وبركاته\n"
        f"📅 {date_str}\n\n"
        "خادم القرآن الرقمي 💫\n"
        f"{status_text}\nقائمة تسجيل الأدوار 📝\n\n"
        f"✍️ المسجلات:\n{section('register')}\n\n"
        f"⛔️ المعتذرات:\n{section('excused')}\n\n"
        f"🎧 المستمعات:\n{section('listener')}\n\n"
        f"🚫 المحظورات:\n{section('banned')}\n\n"
        "وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ۚ وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ"
    )

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ قرأت", callback_data="read"), InlineKeyboardButton("✍️ سجل اسمي", callback_data="register")],
        [InlineKeyboardButton("🎧 مستمعة", callback_data="listener"), InlineKeyboardButton("⛔️ معتذرة", callback_data="excused")],
        [InlineKeyboardButton("🚫 حظر", callback_data="ban"), InlineKeyboardButton("🧹 تصفير", callback_data="reset")],
        [InlineKeyboardButton("🔒 قفل/فتح", callback_data="lock"), InlineKeyboardButton("❌ حذف اسمي", callback_data="remove")]
    ])

# 3. المعالجات (تم تعريفها هنا)
async def start(update, context):
    text = await build(update.effective_chat.id)
    await update.message.reply_text(text, reply_markup=menu())

async def buttons(update, context):
    q = update.callback_query
    await q.answer()
    chat_id = q.message.chat_id
    user_id = q.from_user.id
    action = q.data
    conn = await get_db()
    
    if action in ["register", "listener", "excused", "ban"]:
        if action == "ban":
            await conn.execute("UPDATE users SET status='banned' WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        else:
            if await get_locked(chat_id): return
            await conn.execute("INSERT OR REPLACE INTO users (chat_id,user_id,name,status,read_status) VALUES (?,?,?,?,0)", (chat_id, user_id, q.from_user.full_name, action))
    elif action == "read": 
        await conn.execute("UPDATE users SET read_status = CASE WHEN read_status=0 THEN 1 ELSE 0 END WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    elif action == "remove": await conn.execute("DELETE FROM users WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    elif action == "lock": await conn.execute("UPDATE groups SET locked = CASE WHEN locked=0 THEN 1 ELSE 0 END WHERE chat_id=?", (chat_id,))
    elif action == "reset": await conn.execute("DELETE FROM users WHERE chat_id=?", (chat_id,))
    
    await conn.commit()
    await q.edit_message_text(await build(chat_id), reply_markup=menu())

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CallbackQueryHandler(buttons))

# 4. الـ Webhook المستقر (بدون تدخل الـ loop اليدوي)
@app.route("/webhook", methods=["POST"])
def webhook():
    # تمرير البيانات مباشرة لتليجرام
    json_data = request.get_json(force=True)
    update = Update.de_json(json_data, bot)
    # تشغيل المعالجة في حلقة أحداث جديدة لكل طلب لضمان عدم التعارض
    asyncio.run(bot_app.process_update(update))
    return "ok", 200

@app.route("/")
def home():
    return "Bot is active", 200
