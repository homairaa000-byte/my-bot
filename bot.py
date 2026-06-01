import os
import logging
import asyncio
import aiosqlite
from datetime import datetime
from flask import Flask, request

from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# =====================================
# الإعدادات
# =====================================
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")

DB = "bot.db"
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# إعداد التطبيق (بدون تشغيل التحديثات هنا لأننا نستخدم Webhook)
bot_app = Application.builder().token(TOKEN).build()

# =====================================
# Database Functions
# =====================================
async def get_db():
    conn = await aiosqlite.connect(DB)
    await conn.execute("CREATE TABLE IF NOT EXISTS groups (chat_id INTEGER PRIMARY KEY, locked INTEGER DEFAULT 0)")
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER, user_id INTEGER, name TEXT, 
            status TEXT, read_status INTEGER DEFAULT 0,
            PRIMARY KEY(chat_id, user_id)
        )
    """)
    await conn.commit()
    return conn

async def get_locked(chat_id):
    conn = await get_db()
    try:
        await conn.execute("INSERT OR IGNORE INTO groups(chat_id, locked) VALUES (?,0)", (chat_id,))
        await conn.commit()
        async with conn.execute("SELECT locked FROM groups WHERE chat_id=?", (chat_id,)) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else 0
    finally:
        await conn.close()

# ... (باقي دوال الـ build و menu هي نفسها التي لديك) ...

# =====================================
# Handlers
# =====================================
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
    try:
        # (نفس المنطق الخاص بك مع ضمان إغلاق الاتصال في الـ finally)
        if action in ["register", "listener", "excused", "ban"]:
            if action == "ban":
                await conn.execute("UPDATE users SET status='banned' WHERE chat_id=? AND user_id=?", (chat_id, user_id))
            else:
                if not await get_locked(chat_id):
                    await conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, 0)", 
                                       (chat_id, user_id, q.from_user.full_name, action))
        elif action == "read":
            await conn.execute("UPDATE users SET read_status = CASE WHEN read_status=0 THEN 1 ELSE 0 END WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        elif action == "remove":
            await conn.execute("DELETE FROM users WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        elif action == "lock":
            await conn.execute("UPDATE groups SET locked = CASE WHEN locked=0 THEN 1 ELSE 0 END WHERE chat_id=?", (chat_id,))
        elif action == "reset":
            await conn.execute("DELETE FROM users WHERE chat_id=?", (chat_id,))
        
        await conn.commit()
        await q.edit_message_text(await build(chat_id), reply_markup=menu())
    finally:
        await conn.close()

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CallbackQueryHandler(buttons))

# =====================================
# Webhook Route
# =====================================
@app.route("/webhook", methods=["POST"])
def webhook():
    if request.method == "POST":
        json_data = request.get_json(force=True)
        update = Update.de_json(json_data, bot_app.bot)
        # تشغيل المعالجة داخل حلقة الحدث الحالية
        asyncio.run(bot_app.process_update(update))
    return "ok", 200

if __name__ == "__main__":
    # تهيئة البوت عند بدء التشغيل
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot_app.initialize())
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
