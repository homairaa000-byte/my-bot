import os
import asyncio
import aiosqlite
import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

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
# DATABASE & HELPERS
# =========================
async def get_db():
    conn = await aiosqlite.connect(DB)
    await conn.execute("PRAGMA journal_mode=WAL;")
    await conn.execute("CREATE TABLE IF NOT EXISTS groups (chat_id INTEGER PRIMARY KEY, locked INTEGER DEFAULT 0)")
    await conn.execute("CREATE TABLE IF NOT EXISTS users (chat_id INTEGER, user_id INTEGER, name TEXT, status TEXT, read_status INTEGER DEFAULT 0, PRIMARY KEY(chat_id, user_id))")
    await conn.commit()
    return conn

async def is_admin(update, context):
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        return member.status in ["creator", "administrator"]
    except: return False

async def build(chat_id, conn):
    await conn.execute("INSERT OR IGNORE INTO groups(chat_id, locked) VALUES (?,0)", (chat_id,))
    cur = await conn.execute("SELECT locked FROM groups WHERE chat_id=?", (chat_id,))
    row = await cur.fetchone()
    locked = row[0] if row else 0
    cur = await conn.execute("SELECT name,status,read_status FROM users WHERE chat_id=?", (chat_id,))
    data = await cur.fetchall()
    
    def section(status):
        res = [f"{n}{' ✅' if r == 1 else ''}" for n, s, r in data if s == status]
        return "\n".join(f"{i+1}- {x}" for i, x in enumerate(res)) if res else "لا يوجد"
    
    return f"خادم القرآن الرقمي 💫\n{'🔒 التسجيل مغلق' if locked else '🔓 التسجيل مفتوح'}\n\n✍️ المسجلات:\n{section('register')}\n\n⛔️ المعتذرات:\n{section('excused')}\n\n🎧 المستمعات:\n{section('listener')}\n\n🚫 المحظورات:\n{section('banned')}"

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ قرأت", callback_data="read"), InlineKeyboardButton("✍️ سجل", callback_data="register")],
        [InlineKeyboardButton("🎧 مستمعة", callback_data="listener"), InlineKeyboardButton("⛔️ معتذرة", callback_data="excused")],
        [InlineKeyboardButton("🔒 قفل/فتح", callback_data="lock"), InlineKeyboardButton("🧹 تصفير", callback_data="reset")],
        [InlineKeyboardButton("❌ حذف", callback_data="remove")]
    ])

# =========================
# HANDLERS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = await get_db()
    text = await build(update.effective_chat.id, conn)
    await conn.close()
    await update.message.reply_text(text, reply_markup=menu())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id, user_id, action = q.message.chat_id, q.from_user.id, q.data
    conn = await get_db()
    try:
        if action in ["lock", "reset"]:
            if await is_admin(update, context):
                if action == "lock":
                    cur = await conn.execute("SELECT locked FROM groups WHERE chat_id=?", (chat_id,))
                    l = (await cur.fetchone())[0]
                    await conn.execute("UPDATE groups SET locked=? WHERE chat_id=?", (0 if l else 1, chat_id))
                else: await conn.execute("DELETE FROM users WHERE chat_id=?", (chat_id,))
        elif action in ["register", "listener", "excused"]:
            await conn.execute("INSERT OR REPLACE INTO users (chat_id, user_id, name, status, read_status) VALUES (?,?,?,?,0)", (chat_id, user_id, q.from_user.first_name, action))
        elif action == "read":
            await conn.execute("INSERT INTO users (chat_id, user_id, name, status, read_status) VALUES (?,?,?,?,1) ON CONFLICT(chat_id,user_id) DO UPDATE SET read_status = 1 - read_status", (chat_id, user_id, q.from_user.first_name, "register"))
        elif action == "remove":
            await conn.execute("DELETE FROM users WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        
        await conn.commit()
        new_text = await build(chat_id, conn)
        await q.edit_message_text(new_text, reply_markup=menu())
    finally: await conn.close()

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CallbackQueryHandler(buttons))

# =========================
# WEBHOOK
# =========================
@flask_app.route("/", methods=["GET"])
def home(): return "Bot is running", 200

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    asyncio.run_coroutine_threadsafe(bot_app.process_update(Update.de_json(request.get_json(force=True), bot_app.bot)), asyncio.get_event_loop())
    return "ok", 200

