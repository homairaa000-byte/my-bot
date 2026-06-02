import os
import asyncio
import aiosqlite
from datetime import datetime
import logging
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
    await conn.execute("CREATE TABLE IF NOT EXISTS groups (chat_id INTEGER PRIMARY KEY, locked INTEGER DEFAULT 0)")
    await conn.execute("CREATE TABLE IF NOT EXISTS users (chat_id INTEGER, user_id INTEGER, name TEXT, status TEXT, read_status INTEGER DEFAULT 0, PRIMARY KEY(chat_id, user_id))")
    await conn.commit()
    return conn

async def is_admin(update, context):
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        return member.status in ['creator', 'administrator']
    except: return False

async def build(chat_id, conn):
    async with conn.execute("INSERT OR IGNORE INTO groups(chat_id, locked) VALUES (?,0)", (chat_id,)): pass
    async with conn.execute("SELECT locked FROM groups WHERE chat_id=?", (chat_id,)) as c:
        row = await c.fetchone()
        locked = row[0]
    async with conn.execute("SELECT name,status,read_status FROM users WHERE chat_id=?", (chat_id,)) as c:
        data = await c.fetchall()
    
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
        "\n\u200B"
    )

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ قرأت", callback_data="read"), InlineKeyboardButton("✍️ سجل اسمي", callback_data="register")],
        [InlineKeyboardButton("🎧 مستمعة", callback_data="listener"), InlineKeyboardButton("⛔️ معتذرة", callback_data="excused")],
        [InlineKeyboardButton("🚫 حظر", callback_data="ban"), InlineKeyboardButton("🧹 تصفير", callback_data="reset")],
        [InlineKeyboardButton("🔒 قفل/فتح", callback_data="lock"), InlineKeyboardButton("❌ حذف اسمي", callback_data="remove")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = await get_db()
    text = await build(update.effective_chat.id, conn)
    await conn.close()
    await update.message.reply_text(text, reply_markup=menu())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = q.message.chat_id
    user_id = q.from_user.id
    action = q.data
    conn = await get_db()

    # 1. الحماية والحظر
    if action in ["lock", "reset"]:
        if not await is_admin(update, context):
            await conn.close()
            return await q.answer("❌ هذا الأمر خاص بالمشرفات فقط!", show_alert=True)
        if action == "lock": await conn.execute("UPDATE groups SET locked = NOT locked WHERE chat_id=?", (chat_id,))
        if action == "reset": await conn.execute("DELETE FROM users WHERE chat_id=? AND status != 'banned'", (chat_id,))
    
    else:
        # فحص الحظر العام لكل الأفعال
        async with conn.execute("SELECT status FROM users WHERE chat_id=? AND user_id=?", (chat_id, user_id)) as c:
            row = await c.fetchone()
            if row and row[0] == 'banned' and action != "ban":
                await conn.close()
                return await q.answer("أنتِ محظورة!", show_alert=True)

        if action == "ban":
            await conn.execute("INSERT OR REPLACE INTO users (chat_id, user_id, name, status) VALUES (?, ?, ?, 'banned')", (chat_id, user_id, q.from_user.first_name))
        elif action in ["register", "listener", "excused"]:
            async with conn.execute("SELECT locked FROM groups WHERE chat_id=?", (chat_id,)) as c:
                row = await c.fetchone()
                if row and row[0] == 1:
                    await conn.close()
                    return await q.answer("التسجيل مغلق!", show_alert=True)
            await conn.execute("INSERT OR REPLACE INTO users (chat_id, user_id, name, status) VALUES (?, ?, ?, ?)", (chat_id, user_id, q.from_user.first_name, action))
        elif action == "read":
            await conn.execute("UPDATE users SET read_status = NOT read_status WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        elif action == "remove":
            await conn.execute("DELETE FROM users WHERE chat_id=? AND user_id=?", (chat_id, user_id))

    await conn.commit()
    new_text = await build(chat_id, conn)
    await conn.close()
    await q.edit_message_text(text=new_text, reply_markup=menu())

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CallbackQueryHandler(buttons))

# =========================
# WEBHOOK (STABLE LOOP)
# =========================
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot_app.bot)
    async def process():
        if not bot_app.running: await bot_app.initialize()
        await bot_app.process_update(update)
    loop.create_task(process())
    return "ok", 200
