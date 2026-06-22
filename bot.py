import os
import asyncio
from datetime import datetime
from aiohttp import web
import asyncpg

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
    ContextTypes,
)

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 10000))
DATABASE_URL = os.getenv("DATABASE_URL")

if not TOKEN:
    raise ValueError("BOT_TOKEN is missing")
if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL is missing")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing")

# =========================
# APPLICATION
# =========================
app = Application.builder().token(TOKEN).build()

# =========================
# INIT DB (PRODUCTION SAFE)
# =========================
async def init_db():
    conn = await asyncpg.connect(DATABASE_URL)

    await conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        chat_id BIGINT,
        user_id BIGINT,
        name TEXT,
        status TEXT,
        read_status BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP
    )
    """)

    await conn.execute("""
    CREATE TABLE IF NOT EXISTS groups (
        chat_id BIGINT PRIMARY KEY,
        locked BOOLEAN DEFAULT FALSE
    )
    """)

    await conn.close()

# =========================
# ADMIN CHECK
# =========================
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id,
            update.effective_user.id
        )
        return member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except:
        return False

# =========================
# TEXTS (كما هي بدون حذف)
# =========================
WELCOME_MESSAGE = """
مرحبا مرحبا بوصية رسول الله...
قال رسول الله ﷺ: "سيأتيكُم أقوامٌ يطلبونَ العِلمَ، فإذا رأيتُموهم فقولوا لَهُم: مَرحبًا مَرحبًا بوصيَّةِ رسولِ اللَّهِ صلَّى اللَّهُ عليهِ وسلَّمَ، واقْنوهُم". قلتُ للحَكَمِ: ما اقْنوهُم؟ قالَ: علِّموهُم.

أهلاً بكِ في أكاديمية معارج الإتقان 🕊🌴🌴🌴
يرجى قراءة القوانين والالتزام بها.
"""

RULES_TEXT = """
بسم الله الرحمن الرحيم 

أكاديمية معارج الاتقان 🕊🌴🌴🌴

قوانين الأكاديمية:

🌴🌴 الأكاديمية تعنى بتقديم كل ما يتعلق بالقرآن والتجويد.

1. الأكاديمية خاصة بالنساء فقط 🚫
2. الالتزام مطلوب 👩‍✈️
3. يمنع الرموز في الأسماء ❌
4. الالتزام بالمجموعات التعليمية
5. ممنوع نشر الروابط 🛑
6. ممنوع التواصل الخاص ✋
"""

SCHEDULE_TEXT = """
📅 جدول حلقات المقرأة

💐 المعلمة : لطيفة
📝 تصحيح تلاوة
⏰ الإثنين 12 مكة

💐 المعلمة : لطيفة
📝 المخارج
⏰ الثلاثاء 12 مكة

💐 المعلمة : عالية محمد
⏰ 6:00 مساء مكة

💐 المعلمة : مريم ياسين
⏰ 3 مساء ليبيا

🌿 القرآن في الدنيا نافع وفي القبر شافع وفي الجنة رافع
"""

HELP_TEXT = """
🌸 الأوامر:
/start - تشغيل البوت
/help - المساعدة
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
# REGISTER HANDLERS
# =========================
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CallbackQueryHandler(buttons))

# =========================
# WEBHOOK HANDLER
# =========================
async def handle(request):
    data = await request.json()
    update = Update.de_json(data, app.bot)
    await app.process_update(update)
    return web.Response(text="OK")

# =========================
# START SERVER
# =========================
async def run():
    # 🔥 إصلاح أهم خطأ في PTB 22+
    await app.initialize()
    await app.start()

    # إنشاء الجداول تلقائياً
    await init_db()

    webhook_path = f"/{TOKEN}"

    await app.bot.set_webhook(
        url=f"{WEBHOOK_URL}{webhook_path}"
    )

    aio_app = web.Application()
    aio_app.router.add_post(webhook_path, handle)
    aio_app.router.add_get("/", lambda r: web.Response(text="Bot is running"))

    runner = web.AppRunner(aio_app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    print("🚀 BOT IS LIVE ON RENDER")

    while True:
        await asyncio.sleep(3600)

# =========================
# RUN
# =========================
if __name__ == "__main__":
    asyncio.run(run())
