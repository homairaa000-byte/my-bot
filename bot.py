import os
import sqlite3
import logging

from fastapi import FastAPI, Request
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Bot
)

# =====================================
# الإعدادات
# =====================================

TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
WEBHOOK_URL = f"{RENDER_URL}/webhook"

if not TOKEN:
    raise Exception("BOT_TOKEN missing")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
bot = Bot(token=TOKEN)

DB = "bot.db"

# =====================================
# DB
# =====================================

def db():
    return sqlite3.connect(DB)

def init():
    with db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS groups(
            chat_id INTEGER PRIMARY KEY,
            locked INTEGER DEFAULT 0
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS users(
            chat_id INTEGER,
            user_id INTEGER,
            name TEXT,
            status TEXT,
            is_banned INTEGER DEFAULT 0,
            read_status INTEGER DEFAULT 0,
            PRIMARY KEY(chat_id, user_id)
        )
        """)

init()

# =====================================
# UI MENU (نفس تنسيقك الأصلي)
# =====================================

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
# BUILD TEXT (نفس تنسيقك)
# =====================================

def get_locked(chat_id):
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO groups(chat_id,locked) VALUES(?,0)", (chat_id,))
        row = conn.execute("SELECT locked FROM groups WHERE chat_id=?", (chat_id,)).fetchone()
        return row[0] if row else 0


def build(chat_id):
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO groups(chat_id,locked) VALUES(?,0)", (chat_id,))

        locked = get_locked(chat_id)

        data = conn.execute("""
            SELECT name,status,is_banned,read_status
            FROM users WHERE chat_id=?
        """, (chat_id,)).fetchall()

    status_text = "🔒 التسجيل مغلق" if locked else "🔓 التسجيل مفتوح"

    def section(status, banned=False):
        res = []

        for name, st, b, rd in data:

            if banned and b == 1:
                res.append(name)

            elif not banned and st == status:
                mark = " ✅" if (st == "register" and rd == 1) else ""
                res.append(f"{name}{mark}")

        return "لا يوجد" if not res else "\n".join(
            f"{i+1}- {x}" for i, x in enumerate(res)
        )

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

# =====================================
# WEBHOOK HANDLER
# =====================================

@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, bot)

    # ======================
    # MESSAGE HANDLER
    # ======================
    if update.message:
        chat_id = update.effective_chat.id
        text = update.message.text

        if text == "/start":
            await bot.send_message(
                chat_id,
                build(chat_id),
                reply_markup=menu()
            )

    # ======================
    # CALLBACK HANDLER
    # ======================
    elif update.callback_query:
        q = update.callback_query
        await q.answer()

        chat_id = q.message.chat.id
        user_id = q.from_user.id
        action = q.data

        locked = get_locked(chat_id)

        with db() as conn:

            # تسجيل
            if action in ["register", "listener", "excused"]:

                if locked:
                    await q.answer("التسجيل مغلق حالياً", show_alert=True)
                    return {"ok": True}

                conn.execute("""
                    INSERT OR REPLACE INTO users
                    (chat_id,user_id,name,status,read_status)
                    VALUES (?,?,?,?,0)
                """, (
                    chat_id,
                    user_id,
                    q.from_user.full_name,
                    action
                ))

            # قرأت
            elif action == "read":
                conn.execute("""
                    UPDATE users SET read_status=1
                    WHERE chat_id=? AND user_id=?
                """, (chat_id, user_id))

            # حذف
            elif action == "remove":
                conn.execute("""
                    DELETE FROM users
                    WHERE chat_id=? AND user_id=?
                """, (chat_id, user_id))

            # تصفير (كل الأسماء)
            elif action == "reset":
                conn.execute("DELETE FROM users WHERE chat_id=?", (chat_id,))

            # فتح / قفل
            elif action == "lock":
                conn.execute("""
                    UPDATE groups
                    SET locked = CASE WHEN locked=0 THEN 1 ELSE 0 END
                    WHERE chat_id=?
                """, (chat_id,))

        await bot.edit_message_text(
            build(chat_id),
            chat_id,
            q.message.message_id,
            reply_markup=menu()
        )

    return {"ok": True}

# =====================================
# HEALTH CHECK
# =====================================

@app.get("/")
def home():
    return "Bot is running"

# =====================================
# START WEBHOOK
# =====================================

@app.on_event("startup")
async def startup():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
