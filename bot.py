import os
import asyncio
import aiosqlite
import logging
from datetime import datetime
from flask import Flask, request

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)

# =========================
# SETTINGS
# =========================
TOKEN = os.getenv("BOT_TOKEN")
DB = "bot.db"
logging.basicConfig(level=logging.INFO)

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")

# =========================
# BOT & FLASK
# =========================
bot_app = Application.builder().token(TOKEN).build()
flask_app = Flask(__name__)

# =========================
# EVENT LOOP
# =========================
loop = asyncio.get_event_loop()

async def init_bot():
    logging.info("Initializing bot application...")
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start()
    logging.info("Bot application started successfully.")

loop.create_task(init_bot())

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
# ADMIN CHECK
# =========================
async def is_admin(update, context):
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id,
            update.effective_user.id
        )
        return member.status in ["creator", "administrator"]
    except Exception as e:
        logging.error(f"Admin check error: {e}", exc_info=True)
        return False

# =========================
# UI BUILDER
# =========================
async def build(chat_id, conn):
    await conn.execute(
        "INSERT OR IGNORE INTO groups(chat_id, locked) VALUES (?,0)",
        (chat_id,)
    )
    cur = await conn.execute("SELECT locked FROM groups WHERE chat_id=?", (chat_id,))
    row = await cur.fetchone()
    locked = row[0] if row else 0

    cur = await conn.execute(
        "SELECT name,status,read_status FROM users WHERE chat_id=?",
        (chat_id,)
    )
    data = await cur.fetchall()

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
        f"{status_text}\n\n"
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
        [
            InlineKeyboardButton("✅ قرأت", callback_data="read"),
            InlineKeyboardButton("✍️ سجل", callback_data="register")
        ],
        [
            InlineKeyboardButton("🎧 مستمعة", callback_data="listener"),
            InlineKeyboardButton("⛔️ معتذرة", callback_data="excused")
        ],
        [
            InlineKeyboardButton("🔒 قفل/فتح", callback_data="lock"),
            InlineKeyboardButton("🧹 تصفير", callback_data="reset")
        ],
        [
            InlineKeyboardButton("❌ حذف", callback_data="remove")
        ]
    ])

# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"/start command received from chat_id={update.effective_chat.id}")
    conn = await get_db()
    text = await build(update.effective_chat.id, conn)
    await conn.close()
    await update.message.reply_text(text, reply_markup=menu())

# =========================
# CALLBACKS
# =========================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    try:
        await q.answer()
    except:
        pass

    chat_id = q.message.chat_id
    user_id = q.from_user.id
    action = q.data
    logging.info(f"Callback received: chat_id={chat_id}, user_id={user_id}, action={action}")

    conn = await get_db()
    try:
        if action in ["lock", "reset"]:
            if not await is_admin(update, context):
                await conn.close()
                return await q.answer("❌ للمشرفات فقط", show_alert=True)

            if action == "lock":
                cur = await conn.execute("SELECT locked FROM groups WHERE chat_id=?", (chat_id,))
                row = await cur.fetchone()
                locked = row[0] if row else 0
                await conn.execute(
                    "UPDATE groups SET locked=? WHERE chat_id=?",
                    (0 if locked else 1, chat_id)
                )
                logging.info(f"Lock toggled for chat_id={chat_id}")
            elif action == "reset":
                await conn.execute("DELETE FROM users WHERE chat_id=?", (chat_id,))
                logging.info(f"Users reset for chat_id={chat_id}")
        else:
            cur = await conn.execute(
                "SELECT status FROM users WHERE chat_id=? AND user_id=?",
                (chat_id, user_id)
            )
            row = await cur.fetchone()
            if row and row[0] == "banned":
                await conn.close()
                return await q.answer("🚫 محظور", show_alert=True)

            if action in ["register", "listener", "excused"]:
                cur = await conn.execute("SELECT
