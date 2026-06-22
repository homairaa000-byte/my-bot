import os
import sqlite3
import asyncio
from datetime import datetime
from aiohttp import web

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatMember
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 10000))

if not TOKEN:
    raise ValueError("BOT_TOKEN is missing")
if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL is missing")

# =========================
# DATABASE (SQLite)
# =========================
DB_PATH = "bot.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        chat_id INTEGER,
        user_id INTEGER,
        name TEXT,
        status TEXT,
        read_status INTEGER DEFAULT 0,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS groups (
        chat_id INTEGER PRIMARY KEY,
        locked INTEGER DEFAULT 0
    )
    """)

    conn.commit()
    conn.close()

init_db()

def add_user(chat_id, user_id, name):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
        (chat_id, user_id, name, "active", 0, str(datetime.utcnow()))
    )
    conn.commit()
    conn.close()

# =========================
# APPLICATION
# =========================
app = Application.builder().token(TOKEN).build()

# =========================
# TEXTS (كما هي بدون حذف)
# =========================
WELCOME_MESSAGE = """
مرحبا مرحبا بوصية رسول الله...
قال رسول الله ﷺ: "سيأتيكُم أقوامٌ يطلبونَ العِلمَ، فإذا رأيتُموهم فقولوا لَهُم: مَرحبًا مَرحبًا بوصيَّةِ رسولِ اللَّهِ صلَّى اللَّهُ عليهِ وسلَّمَ، واقْنوهُم". قلتُ للحَكَمِ: ما اقْنوهُم؟ قالَ: علِّموهُم.

أهلاً بكِ في أكاديمية معارج الإتقان 🕊🌴🌴🌴
"""

RULES_TEXT = """
بسم الله الرحمن الرحيم 

أكاديمية معارج الاتقان 🕊🌴🌴🌴

قوانين الأكاديمية:

1. الأكاديمية خاصة بالنساء فقط 🚫
2. الالتزام مطلوب 👩‍✈️
3. يمنع الرموز في الأسماء ❌
4. الالتزام بالمجموعات التعليمية
5. ممنوع نشر الروابط 🛑
6. ممنوع الخاص ✋
"""

SCHEDULE_TEXT = """
📅 جدول حلقات المقرأة

💐 المعلمة : لطيفة
⏰ الإثنين 12 مكة

💐 المعلمة : مريم
⏰ الثلاثاء 3 ليبيا

🌿 القرآن نافع في الدنيا والآخرة
"""

HELP_TEXT = """
🌸 الأوامر:
/start - تشغيل
/help - مساعدة
"""

# =========================
# MENU
# =========================
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 القوانين", callback_data="rules")],
        [InlineKeyboardButton("📅 الجدول", callback_data="schedule")],
        [InlineKeyboardButton("❌ إغلاق", callback_data="close")]
    ])

# =========================
# COMMANDS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    add_user(chat.id, user.id, user.full_name)

    await update.message.reply_text(WELCOME_MESSAGE, reply_markup=menu())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)

# =========================
# BUTTONS
# =========================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "rules":
        await q.edit_message_text(RULES_TEXT, reply_markup=menu())

    elif q.data == "schedule":
        await q.edit_message_text(SCHEDULE_TEXT, reply_markup=menu())

    elif q.data == "close":
        await q.edit_message_text("تم الإغلاق.")

# =========================
# HANDLERS
# =========================
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CallbackQueryHandler(buttons))

# =========================
# WEBHOOK SERVER (FIXED + RENDER SAFE)
# =========================
async def handle(request):
    data = await request.json()
    update = Update.de_json(data, app.bot)
    await app.process_update(update)
    return web.Response(text="OK")

async def run():
    await app.initialize()
    await app.start()

    webhook_path = f"/{TOKEN}"

    await app.bot.set_webhook(url=f"{WEBHOOK_URL}{webhook_path}")

    aio_app = web.Application()
    aio_app.router.add_post(webhook_path, handle)
    aio_app.router.add_get("/", lambda r: web.Response(text="Bot is running"))

    runner = web.AppRunner(aio_app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    print("🚀 Bot is running on Render")

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(run())
