import os
import logging
import asyncio
import aiosqlite
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# =====================================
# الإعدادات
# =====================================
TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", "10000"))
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
WEBHOOK_URL = f"{RENDER_URL}/webhook" if RENDER_URL else None
DB = "bot.db"

if not TOKEN:
    raise ValueError("BOT_TOKEN is missing")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
bot_app = Application.builder().token(TOKEN).build()

# =====================================
# Database (Async)
# =====================================
async def init_db():
    async with aiosqlite.connect(DB) as conn:
        await conn.execute("CREATE TABLE IF NOT EXISTS groups (chat_id INTEGER PRIMARY KEY, locked INTEGER DEFAULT 0)")
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER, user_id INTEGER, name TEXT, status TEXT,
            read_status INTEGER DEFAULT 0, PRIMARY KEY(chat_id, user_id)
        )
        """)
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
        "وَلَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ۚ وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ"
    )

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ قرأت", callback_data="read"), InlineKeyboardButton("✍️ سجل اسمي", callback_data="register")],
        [InlineKeyboardButton("🎧 مستمعة", callback_data="listener"), InlineKeyboardButton("⛔️ معتذرة", callback_data="excused")],
        [InlineKeyboardButton("🧹 تصفير", callback_data="reset"), InlineKeyboardButton("🔒 قفل/فتح", callback_data="lock")],
        [InlineKeyboardButton("❌ حذف اسمي", callback_data="remove")]
    ])

# =====================================
# Handlers
# =====================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = await build(update.effective_chat.id)
    await update.message.reply_text(text, reply_markup=menu())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = q.message.chat_id
    user_id = q.from_user.id
    action = q.data

    async with aiosqlite.connect(DB) as conn:
        locked = await get_locked(chat_id)
        if action in ["register", "listener", "excused"]:
            if locked:
                await q.answer("التسجيل مغلق حالياً", show_alert=True)
                return
            await conn.execute("INSERT OR REPLACE INTO users (chat_id,user_id,name,status,read_status) VALUES (?,?,?,?,0)", 
                               (chat_id, user_id, q.from_user.full_name, action))
        elif action == "read":
            await conn.execute("UPDATE users SET read_status=1 WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        elif action == "remove":
            await conn.execute("DELETE FROM users WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        elif action == "lock":
            await conn.execute("UPDATE groups SET locked = CASE WHEN locked=0 THEN 1 ELSE 0 END WHERE chat_id=?", (chat_id,))
        elif action == "reset":
            await conn.execute("DELETE FROM users WHERE chat_id=?", (chat_id,))
        await conn.commit()

    await q.edit_message_text(await build(chat_id), reply_markup=menu())

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CallbackQueryHandler(buttons))

# =====================================
# Webhook & Flask
# =====================================
@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    asyncio.run(bot_app.process_update(update))
    return "ok", 200

@app.route("/")
def home():
    return "Bot is running", 200

async def setup():
    await init_db()
    if WEBHOOK_URL:
        await bot_app.bot.set_webhook(WEBHOOK_URL)

if __name__ == "__main__":
    asyncio.run(setup())
    app.run(host="0.0.0.0", port=PORT)
