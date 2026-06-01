import os
import logging
import sqlite3
import asyncio
import threading

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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

app = Flask(__name__)

# =====================================
# Telegram App
# =====================================

bot_app = Application.builder().token(TOKEN).build()

# =====================================
# Database (مع timeout + Lock)
# =====================================

_db_lock = threading.Lock()

def db():
    return sqlite3.connect(DB, timeout=10, check_same_thread=False)

def init_db():
    with db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            chat_id INTEGER PRIMARY KEY,
            locked INTEGER DEFAULT 0
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER,
            user_id INTEGER,
            name TEXT,
            status TEXT,
            is_banned INTEGER DEFAULT 0,
            read_status INTEGER DEFAULT 0,
            PRIMARY KEY(chat_id, user_id)
        )
        """)

init_db()

# =====================================
# Helpers
# =====================================

def get_locked(chat_id):
    with _db_lock, db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO groups(chat_id, locked) VALUES (?,0)",
            (chat_id,)
        )
        row = conn.execute(
            "SELECT locked FROM groups WHERE chat_id=?",
            (chat_id,)
        ).fetchone()
        return row[0] if row else 0

def build(chat_id):
    with _db_lock, db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO groups(chat_id, locked) VALUES (?,0)",
            (chat_id,)
        )
        locked = get_locked(chat_id)
        data = conn.execute("""
            SELECT name,status,is_banned,read_status
            FROM users
            WHERE chat_id=?
        """, (chat_id,)).fetchall()

    status_text = "🔒 التسجيل مغلق" if locked else "🔓 التسجيل مفتوح"

    def section(status, banned=False):
        result = []
        for name, st, is_banned, read_status in data:
            if banned and is_banned == 1:
                result.append(name)
            elif not banned and st == status:
                mark = ""
                if status == "register" and read_status == 1:
                    mark = " ✅"
                result.append(f"{name}{mark}")
        if not result:
            return "لا يوجد"
        return "\n".join(f"{i+1}- {x}" for i, x in enumerate(result))

    return (
        "السلام عليكم ورحمة الله وبركاته\n\n"
        "خادم القرآن الرقمي 💫\n"
        f"{status_text}\n"
        "قائمة تسجيل الأدوار 📝\n\n"
        f"✍️ المسجلات:\n{section('register')}\n\n"
        f"⛔️ المعتذرات:\n{section('excused')}\n\n"
        f"🎧 المستمعات:\n{section('listener')}\n\n"
        f"🚫 المحظورات:\n{section('', banned=True)}\n\n"
        "وَلَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ۚ "
        "وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ"
    )

def menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ قرأت", callback_data="read"),
            InlineKeyboardButton("✍️ سجل اسمي", callback_data="register")
        ],
        [
            InlineKeyboardButton("🎧 مستمعة", callback_data="listener"),
            InlineKeyboardButton("⛔️ معتذرة", callback_data="excused")
        ],
        [
            InlineKeyboardButton("🧹 تصفير", callback_data="reset"),
            InlineKeyboardButton("🔒 قفل/فتح", callback_data="lock")
        ],
        [
            InlineKeyboardButton("❌ حذف اسمي", callback_data="remove")
        ]
    ])

# =====================================
# Commands
# =====================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        build(update.effective_chat.id),
        reply_markup=menu()
    )

# =====================================
# Buttons
# =====================================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    chat_id = q.message.chat_id
    user_id = q.from_user.id
    action = q.data

    locked = get_locked(chat_id)

    with _db_lock, db() as conn:
        if action in ["register", "listener", "excused"]:
            if locked:
                await q.answer("التسجيل مغلق حالياً", show_alert=True)
                return
            conn.execute("""
                INSERT OR REPLACE INTO users
                (chat_id,user_id,name,status,read_status)
                VALUES (?,?,?,?,0)
            """, (chat_id, user_id, q.from_user.full_name, action))
        elif action == "read":
            conn.execute("""
                UPDATE users SET read_status=1
                WHERE chat_id=? AND user_id=?
            """, (chat_id, user_id))
        elif action == "remove":
            conn.execute("""
                DELETE FROM users WHERE chat_id=? AND user_id=?
            """, (chat_id, user_id))
        elif action == "lock":
            conn.execute("""
                UPDATE groups SET locked = CASE WHEN locked=0 THEN 1 ELSE 0 END
                WHERE chat_id=?
            """, (chat_id,))
        elif action == "reset":
            conn.execute("DELETE FROM users WHERE chat_id=?", (chat_id,))

    try:
        await q.edit_message_text(build(chat_id), reply_markup=menu())
    except Exception:
        pass

# =====================================
# Handlers
# =====================================

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CallbackQueryHandler(buttons))

# =====================================
# FIX EVENT LOOP
# =====================================

def run_async(coro):
    loop = asyncio.new_event_loop()
    return loop.run_until_complete(coro)

# =====================================
# Webhook Startup
# =====================================

async def startup():
    await bot_app.initialize()
    await bot_app.start()
    if WEBHOOK_URL:
        await bot_app.bot.delete_webhook(drop_pending_updates=True)
        await bot_app.bot.set_webhook(WEBHOOK_URL)

run_async(startup())

# =====================================
# Flask Routes
# =====================================

@app.route("/")
def home():
    return "Bot is running", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot_app.bot)
        run_async(bot_app.process_update(update))
        return "ok", 200
    except Exception as e:
        logger.exception(e)
        return "error", 500

# =====================================
# تشغيل مباشر لو محتاج
# =====================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
