import os
import logging
import asyncio
import aiosqlite
import threading
from datetime import datetime
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# 1. الإعدادات
TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", "10000"))
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
WEBHOOK_URL = f"{RENDER_URL}/webhook" if RENDER_URL else None
DB = "bot.db"

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

db_conn = None
async def get_db():
    global db_conn
    if db_conn is None:
        db_conn = await aiosqlite.connect(DB)
        await db_conn.execute("CREATE TABLE IF NOT EXISTS groups (chat_id INTEGER PRIMARY KEY, locked INTEGER DEFAULT 0)")
        await db_conn.execute("CREATE TABLE IF NOT EXISTS users (chat_id INTEGER, user_id INTEGER, name TEXT, status TEXT, read_status INTEGER DEFAULT 0, PRIMARY KEY(chat_id, user_id))")
        await db_conn.commit()
    return db_conn

bot_app = Application.builder().token(TOKEN).build()
init_lock = threading.Lock()
initialized = False

def ensure_initialized():
    global initialized
    if not initialized:
        with init_lock:
            if not initialized:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(bot_app.initialize())
                loop.run_until_complete(get_db())
                loop.run_until_complete(bot_app.start())
                if WEBHOOK_URL:
                    loop.run_until_complete(bot_app.bot.set_webhook(WEBHOOK_URL))
                initialized = True

# 2. الدوال الأساسية (تم الإبقاء عليها كما هي)
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

# 3. المعالجات
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

# 4. معالجة الـ Webhook بدون إغلاق الحلقة (مستقر)
@app.route("/webhook", methods=["POST"])
def webhook():
    ensure_initialized()
    json_data = request.get_json(force=True)
    update = Update.de_json(json_data, bot_app.bot)
    # نستخدم asyncio لإنشاء المهمة بدلاً من إدارة الحلقة يدوياً
    asyncio.run_coroutine_threadsafe(bot_app.process_update(update), asyncio.get_event_loop())
    return "ok", 200

@app.route("/")
def home():
    return "Bot is active", 200
