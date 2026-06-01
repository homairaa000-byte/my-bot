import os
import logging
import asyncio
import aiosqlite
from datetime import datetime
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# =========================
# SETTINGS
# =========================

TOKEN = os.getenv("BOT_TOKEN")
DB = "bot.db"

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

bot = Bot(TOKEN)
bot_app = Application.builder().token(TOKEN).build()

# =========================
# INIT FIX (IMPORTANT)
# =========================

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

initialized = False

async def init_bot():
    global initialized
    if not initialized:
        await bot_app.initialize()
        initialized = True


# =========================
# DATABASE (FIXED CONNECTION HANDLING)
# =========================

async def get_db():
    conn = await aiosqlite.connect(DB)

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
# FUNCTIONS
# =========================

async def get_locked(chat_id):
    conn = await get_db()

    await conn.execute(
        "INSERT OR IGNORE INTO groups(chat_id, locked) VALUES (?,0)",
        (chat_id,)
    )

    async with conn.execute(
        "SELECT locked FROM groups WHERE chat_id=?",
        (chat_id,)
    ) as c:
        row = await c.fetchone()

    await conn.close()
    return row[0] if row else 0


async def build(chat_id):
    conn = await get_db()

    locked = await get_locked(chat_id)

    async with conn.execute(
        "SELECT name,status,read_status FROM users WHERE chat_id=?",
        (chat_id,)
    ) as c:
        data = await c.fetchall()

    await conn.close()

    status_text = "🔒 التسجيل مغلق" if locked else "🔓 التسجيل مفتوح"
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    def section(status):
        result = [
            f"{name}{' ✅' if r == 1 else ''}"
            for name, s, r in data if s == status
        ]
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


# =========================
# MENU
# =========================

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
# HANDLERS (FIXED FAST RESPONSE)
# =========================

async def start(update, context):
    text = await build(update.effective_chat.id)
    await update.message.reply_text(text, reply_markup=menu())


async def buttons(update, context):
    q = update.callback_query
    await q.answer(cache_time=0)

    chat_id = q.message.chat.id
    user_id = q.from_user.id
    action = q.data

    conn = await get_db()

    if action in ["register", "listener", "excused", "ban"]:

        if action == "ban":
            await conn.execute(
                "UPDATE users SET status='banned' WHERE chat_id=? AND user_id=?",
                (chat_id, user_id)
            )
