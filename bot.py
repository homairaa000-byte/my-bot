import os
import asyncio
from datetime import datetime
from aiohttp import web
import asyncpg

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
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
DATABASE_URL = os.getenv("DATABASE_URL")
PORT = int(os.getenv("PORT", 10000))

if not TOKEN:
    raise ValueError("BOT_TOKEN is missing")
if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL is missing")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing")

# =========================
# APP
# =========================
app = Application.builder().token(TOKEN).build()

# =========================
# TEXTS (كما هي)
# =========================
WELCOME_MESSAGE = """
مرحبا مرحبا بوصية رسول الله...
قال رسول الله ﷺ: "سيأتيكُم أقوامٌ يطلبونَ العِلمَ..."
أهلاً بكِ في أكاديمية معارج الإتقان 🕊🌴🌴🌴
"""

RULES_TEXT = """
بسم الله الرحمن الرحيم 

أكاديمية معارج الاتقان 🕊🌴🌴🌴

1. الأكاديمية خاصة بالنساء فقط 🚫
2. الالتزام مطلوب 👩‍✈️
3. يمنع الرموز ❌
4. ممنوع الروابط 🛑
5. ممنوع الخاص ✋
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
/start
/help
/ban (رد)
/unban (رد)
"""

# =========================
# KEYBOARD
# =========================
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ سجل", callback_data="register"),
         InlineKeyboardButton("🎧 مستمعة", callback_data="listener")],
        [InlineKeyboardButton("⛔ معتذرة", callback_data="excused"),
         InlineKeyboardButton("❌ حذف", callback_data="remove")],
        [InlineKeyboardButton("🔒 قفل/فتح", callback_data="lock"),
         InlineKeyboardButton("🧹 تصفير", callback_data="reset")],
        [InlineKeyboardButton("✔ قرأت", callback_data="read")]
    ])

# =========================
# DB
# =========================
async def get_db():
    return await asyncpg.connect(DATABASE_URL)

async def get_locked(chat_id):
    conn = await get_db()
    await conn.execute("""
        INSERT INTO groups(chat_id, locked)
        VALUES($1, FALSE)
        ON CONFLICT (chat_id) DO NOTHING
    """, chat_id)

    row = await conn.fetchrow("SELECT locked FROM groups WHERE chat_id=$1", chat_id)
    await conn.close()
    return row["locked"] if row else False

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
# BUILD MESSAGE
# =========================
async def build(chat_id):
    conn = await get_db()

    locked = await get_locked(chat_id)
    rows = await conn.fetch(
        "SELECT name,status,read_status FROM users WHERE chat_id=$1 ORDER BY created_at ASC",
        chat_id
    )
    await conn.close()

    def section(status):
        items = [
            f"{r['name']}{' ✔' if r['read_status'] else ''}"
            for r in rows if r["status"] == status
        ]
        return "\n".join(f"{i+1}- {x}" for i, x in enumerate(items)) if items else "لا يوجد"

    return (
        "السلام عليكم ورحمة الله وبركاته\n\n"
        f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        "خادم القرآن الرقمي 💫\n"
        f"{'🔒 التسجيل مغلق' if locked else '🔓 التسجيل مفتوح'}\n\n"
        f"✍️ المسجلات:\n{section('register')}\n\n"
        f"🎧 المستمعات:\n{section('listener')}\n\n"
        f"⛔ المعتذرات:\n{section('excused')}\n\n"
        f"🚫 المحظورات:\n{section('banned')}\n"
    )

# =========================
# COMMANDS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = await build(update.effective_chat.id)
    await update.message.reply_text(WELCOME_MESSAGE + "\n\n" + text, reply_markup=menu())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)

# =========================
# BAN / UNBAN
# =========================
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return

    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user

        conn = await get_db()
        await conn.execute("""
            INSERT INTO users(chat_id,user_id,name,status,read_status,created_at)
            VALUES($1,$2,$3,'banned',FALSE,$4)
            ON CONFLICT (chat_id,user_id)
            DO UPDATE SET status='banned'
        """, update.effective_chat.id, user.id, user.full_name, datetime.now())

        await conn.close()
        await update.message.reply_text("🚫 تم الحظر")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return

    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user

        conn = await get_db()
        await conn.execute(
            "DELETE FROM users WHERE chat_id=$1 AND user_id=$2",
            update.effective_chat.id, user.id
        )
        await conn.close()

        await update.message.reply_text("✅ تم فك الحظر")

# =========================
# BUTTONS
# =========================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    chat_id = q.message.chat_id
    user_id = q.from_user.id
    name = q.from_user.full_name
    action = q.data

    conn = await get_db()

    user = await conn.fetchrow(
        "SELECT status FROM users WHERE chat_id=$1 AND user_id=$2",
        chat_id, user_id
    )

    if user and user["status"] == "banned":
        await conn.close()
        return

    if action in ["register", "listener", "excused"]:
        if await get_locked(chat_id):
            return await conn.close()

        await conn.execute("""
            INSERT INTO users(chat_id,user_id,name,status,read_status,created_at)
            VALUES($1,$2,$3,$4,FALSE,$5)
            ON CONFLICT (chat_id,user_id)
            DO UPDATE SET status=$4
        """, chat_id, user_id, name, action, datetime.now())

    elif action == "remove":
        await conn.execute(
            "DELETE FROM users WHERE chat_id=$1 AND user_id=$2",
            chat_id, user_id
        )

    elif action == "read":
        await conn.execute("""
            UPDATE users SET read_status = NOT read_status
            WHERE chat_id=$1 AND user_id=$2
        """, chat_id, user_id)

    elif action == "lock":
        if await is_admin(update, context):
            await conn.execute(
                "UPDATE groups SET locked = NOT locked WHERE chat_id=$1",
                chat_id
            )

    elif action == "reset":
        if await is_admin(update, context):
            await conn.execute(
                "DELETE FROM users WHERE chat_id=$1 AND status!='banned'",
                chat_id
            )

    await conn.close()

    try:
        await q.edit_message_text(await build(chat_id), reply_markup=menu())
    except:
        pass

# =========================
# HANDLERS
# =========================
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("ban", ban))
app.add_handler(CommandHandler("unban", unban))
app.add_handler(CallbackQueryHandler(buttons))

# =========================
# WEBHOOK (RENDER FIXED)
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

    print("🚀 BOT RUNNING ON RENDER")

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
