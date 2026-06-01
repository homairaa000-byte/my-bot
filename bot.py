import os
import logging
import asyncio
import aiosqlite
import threading
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

# تهيئة البوت
bot_app = Application.builder().token(TOKEN).build()
init_lock = threading.Lock()
initialized = False

# آلية تهيئة آمنة
def ensure_initialized():
    global initialized
    if not initialized:
        with init_lock:
            if not initialized:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(init_db())
                loop.run_until_complete(bot_app.initialize())
                loop.run_until_complete(bot_app.start())
                if WEBHOOK_URL:
                    loop.run_until_complete(bot_app.bot.set_webhook(WEBHOOK_URL))
                initialized = True

# 2. الدوال الأساسية
async def init_db():
    async with aiosqlite.connect(DB) as conn:
        await conn.execute("CREATE TABLE IF NOT EXISTS groups (chat_id INTEGER PRIMARY KEY, locked INTEGER DEFAULT 0)")
        await conn.execute("CREATE TABLE IF NOT EXISTS users (chat_id INTEGER, user_id INTEGER, name TEXT, status TEXT, read_status INTEGER DEFAULT 0, PRIMARY KEY(chat_id, user_id))")
        await conn.commit()

async def get_locked(chat_id):
    async with aiosqlite.connect(DB) as conn:
        await conn.execute("INSERT OR IGNORE INTO groups(chat_id, locked) VALUES (?,0)", (chat_id,))
        async with conn.execute("SELECT locked FROM groups WHERE chat_id=?", (chat_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def build(chat_id):
    async with aiosqlite.connect(DB) as conn:
        await conn.execute("INSERT OR IGNORE INTO groups(chat_id, locked) VALUES (?,0)", (chat_id,))
        locked = await get_locked(chat_id)
        async with conn.execute("SELECT name,status,read_status FROM users WHERE chat_id=?", (chat_id,)) as cursor:
            data = await cursor.fetchall()
    
    status_text = "🔒 التسجيل مغلق" if locked else "🔓 التسجيل مفتوح"
    def section(status):
        result = [f"{name}{' ✅' if read_status == 1 else ''}" for name, st, read_status in data if st == status]
        return "\n".join(f"{i+1}- {x}" for i, x in enumerate(result)) if result else "لا يوجد"
    
    return (
        "السلام عليكم ورحمة الله وبركاته\n\nخادم القرآن الرقمي 💫\n"
        f"{status_text}\nقائمة تسجيل الأدوار 📝\n\n"
        f"✍️ المسجلات:\n{section('register')}\n\n"
        f"⛔️ المعتذرات:\n{section('excused')}\n\n"
        f"🎧 المستمعات:\n{section('listener')}\n\n"
    )

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ قرأت", callback_data="read"), InlineKeyboardButton("✍️ سجل اسمي", callback_data="register")],
        [InlineKeyboardButton("🎧 مستمعة", callback_data="listener"), InlineKeyboardButton("⛔️ معتذرة", callback_data="excused")],
        [InlineKeyboardButton("🧹 تصفير", callback_data="reset"), InlineKeyboardButton("🔒 قفل/فتح", callback_data="lock")],
        [InlineKeyboardButton("❌ حذف اسمي", callback_data="remove")]
    ])

# 3. معالجات الأوامر
async def start(update, context):
    text = await build(update.effective_chat.id)
    await update.message.reply_text(text, reply_markup=menu())

async def buttons(update, context):
    q = update.callback_query
    await q.answer()
    chat_id = q.message.chat_id
    user_id = q.from_user.id
    action = q.data
    async with aiosqlite.connect(DB) as conn:
        if action in ["register", "listener", "excused"]:
            if await get_locked(chat_id): return
            await conn.execute("INSERT OR REPLACE INTO users (chat_id,user_id,name,status,read_status) VALUES (?,?,?,?,0)", (chat_id, user_id, q.from_user.full_name, action))
        elif action == "read": await conn.execute("UPDATE users SET read_status=1 WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        elif action == "remove": await conn.execute("DELETE FROM users WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        elif action == "lock": await conn.execute("UPDATE groups SET locked = CASE WHEN locked=0 THEN 1 ELSE 0 END WHERE chat_id=?", (chat_id,))
        elif action == "reset": await conn.execute("DELETE FROM users WHERE chat_id=?", (chat_id,))
        await conn.commit()
    await q.edit_message_text(await build(chat_id), reply_markup=menu())

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CallbackQueryHandler(buttons))

# 4. الـ Webhook المحدث
@app.route("/webhook", methods=["POST"])
def webhook():
    ensure_initialized()
    update = Update.de_json(request.get_json(force=
