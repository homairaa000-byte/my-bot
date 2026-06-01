import os
import logging
import aiosqlite
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
DB = "bot.db"

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================
# APP
# =========================

app = Application.builder().token(TOKEN).build()

# =========================
# DB SAFE
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
# BUILD MESSAGE
# =========================

async def build(chat_id):
    conn = await get_db()

    try:
        async with conn.execute(
            "SELECT locked FROM groups WHERE chat_id=?",
            (chat_id,)
        ) as c:
            row = await c.fetchone()

        locked = row[0] if row else 0

        async with conn.execute(
            "SELECT name,status,read_status FROM users WHERE chat_id=?",
            (chat_id,)
        ) as c:
            data = await c.fetchall()

        def section(status):
            result = [
                f"{name}{' ✅' if r == 1 else ''}"
                for name, s, r in data
                if s == status
            ]
            if not result:
                return "لا يوجد"
            return "\n".join(f"{i+1}- {x}" for i, x in enumerate(result))

        return (
            "السلام عليكم ورحمة الله وبركاته\n"
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            "خادم القرآن الرقمي 💫\n"
            f"{'🔒 التسجيل مغلق' if locked else '🔓 التسجيل مفتوح'}\n\n"
            f"✍️ المسجلات:\n{section('register')}\n\n"
            f"⛔️ المعتذرات:\n{section('excused')}\n\n"
            f"🎧 المستمعات:\n{section('listener')}\n\n"
            f"🚫 المحظورات:\n{section('banned')}\n\n"
            "وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا"
        )

    finally:
        await conn.close()


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
            InlineKeyboardButton("🚫 حظر", callback_data="ban"),
            InlineKeyboardButton("🧹 تصفير", callback_data="reset")
        ],
        [
            InlineKeyboardButton("🔒 قفل/فتح", callback_data="lock"),
            InlineKeyboardButton("❌ حذف", callback_data="remove")
        ]
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

    try:
        if action in ["register", "listener", "excused", "ban"]:

            if action == "ban":
                await conn.execute(
                    "UPDATE users SET status='banned' WHERE chat_id=? AND user_id=?",
                    (chat_id, user_id)
                )
            else:
                await conn.execute("""
                    INSERT OR REPLACE INTO users
                    (chat_id, user_id, name, status, read_status)
                    VALUES (?, ?, ?, ?, 0)
                """, (
                    chat_id,
                    user_id,
                    q.from_user.full_name,
                    action
                ))

        elif action == "read":
            await conn.execute("""
                UPDATE users
                SET read_status = CASE WHEN read_status=0 THEN 1 ELSE 0 END
                WHERE chat_id=? AND user_id=?
            """, (chat_id, user_id))

        elif action == "remove":
            await conn.execute(
                "DELETE FROM users WHERE chat_id=? AND user_id=?",
                (chat_id, user_id)
            )

        elif action == "lock":
            await conn.execute("""
                UPDATE groups
                SET locked = CASE WHEN locked=0 THEN 1 ELSE 0 END
                WHERE chat_id=?
            """, (chat_id,))

        elif action == "reset":
            await conn.execute(
                "DELETE FROM users WHERE chat_id=?",
                (chat_id,)
            )

        await conn.commit()

        await q.edit_message_text(await build(chat_id), reply_markup=menu())

    finally:
        await conn.close()


# =========================
# REGISTER HANDLERS
# =========================

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))


# =========================
# WEBHOOK (NO FLASK!)
# =========================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))

    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}",
        )
