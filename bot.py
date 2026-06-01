import os
import asyncio
import aiosqlite
from datetime import datetime
import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# =========================
# SETTINGS
# =========================
TOKEN = os.getenv("BOT_TOKEN")
DB = "bot.db"

logging.basicConfig(level=logging.INFO)

# =========================
# BOT & FLASK
# =========================
bot_app = Application.builder().token(TOKEN).build()
flask_app = Flask(__name__)

# =========================
# DATABASE
# =========================
async def get_db():
    conn = await aiosqlite.connect(DB)
    await conn.execute("PRAGMA journal_mode=WAL;")
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            chat_id INTEGER PRIMARY KEY,
            locked INTEGER DEFAULT 0
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER,
            user_id INTEGER,
            name TEXT,
            status TEXT,
            read_status INTEGER DEFAULT 0,
            PRIMARY KEY(chat_id, user_id)
        )
    """)
    await conn.commit()
    return conn

# =========================
# BUILD MESSAGE
# =========================
async def get_locked(chat_id):
    conn = await get_db()
    await conn.execute("INSERT OR IGNORE INTO groups(chat_id, locked) VALUES (?,0)", (chat_id,))
    async with conn.execute("SELECT locked FROM groups WHERE chat_id=?", (chat_id,)) as c:
        row = await c.fetchone()
    await conn.close()
    return row[0] if row else 0

async def build(chat_id):
    conn = await get_db()
    locked = await get_locked(chat_id)
    async with conn.execute("SELECT name,status,read_status FROM users WHERE chat_id=?", (chat_id,)) as c:
        data = await c.fetchall()
    await conn.close()

    status_text = "🔒 التسجيل مغلق" if locked else "🔓 التسجيل مفتوح"
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    def section(status):
        result = [f"{name}{' ✅' if r == 1 else ''}" for name, s, r in data if s == status]
        return "\n".join(f"{i+1}- {x}" for i, x in enumerate(result)) if result else "لا يوجد"

    return (
        "السلام عليكم ورحمة الله وبركاته\n"
        f"📅 {date_str}\n\n"
        "خادم القرآن الرقمي 💫\n"
        f"{status_text}\n"
        "قائمة تسجيل الأدوار 📝\n\n"
        f"✍️ المسجلات:\n{section('register')}\n\n"
        f"⛔️ المعتذرات:\n{section('excused')}\n\n"
        f"🎧 المستمعات:\n{section('listener')}\n\n"
        f"🚫 المحظورات:\n{section('banned')}\n\n"
        "وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ۚ وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ"
    )

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ قرأت", callback_data="read"),
         InlineKeyboardButton("✍️ سجل اسمي", callback_data="register")],
        [InlineKeyboardButton("🎧 مستمعة", callback_data="listener"),
         InlineKeyboardButton("⛔️ معتذرة", callback_data="excused")],
        [InlineKeyboardButton("🚫 حظر", callback_data="ban"),
         InlineKeyboardButton("🧹 تصفير", callback_data="reset")],
        [InlineKeyboardButton("🔒 قفل/فتح", callback_data="lock"),
         InlineKeyboardButton("❌ حذف اسمي", callback_data="remove")]
    ])

# =========================
# HANDLERS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = await build(update.effective_chat.id)
    await update.message.reply_text(text, reply_markup=menu())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = q.message.chat_id
    user_id = q.from_user.id
    action = q.data
    conn = await get_db()

    if action in ["register", "listener", "excused", "ban"]:
        if action == "ban":
            await conn.execute("INSERT OR REPLACE INTO users (chat_id, user_id, name, status, read_status) VALUES (?, ?, ?, 'banned', 0)", (chat_id, user_id, q.from_user.full_name))
        else:
            if await get_locked(chat_id):
                await conn.close()
                return
            await conn.execute("INSERT OR REPLACE INTO users (chat_id, user_id, name, status, read_status) VALUES (?, ?, ?, ?, 0)", (chat_id, user_id, q.from_user.full_name, action))
    elif action == "read":
        await conn.execute("UPDATE users SET read_status = CASE WHEN read_status=1 THEN 0 ELSE 1 END WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    elif action == "remove":
        await conn.execute("DELETE FROM users WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    elif action == "lock":
        await conn.execute("UPDATE groups SET locked = CASE WHEN locked=1 THEN 0 ELSE 1 END WHERE chat_id=?", (chat_id,))
    elif action == "reset":
        await conn.execute("DELETE FROM users WHERE chat_id=?", (chat_id,))

    await conn.commit()
    await conn.close()
    await q.edit_message_text(await build(chat_id), reply_markup=menu())

# إضافة الهاندلرز للتطبيق
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CallbackQueryHandler(buttons))

# =========================
# WEBHOOK
# =========================
@flask_app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot_app.bot)
    asyncio.run(bot_app.process_update(update))
    return "ok", 200
