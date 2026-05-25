import os
import sqlite3
import re
from datetime import datetime
import pytz

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

TOKEN = os.environ.get("BOT_TOKEN")

# ================= DB =================
conn = sqlite3.connect("students.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    status TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS banned (
    user_id INTEGER PRIMARY KEY,
    name TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

cursor.execute("INSERT OR IGNORE INTO settings VALUES ('locked','false')")
conn.commit()

# ================= BOT =================
application = Application.builder().token(TOKEN).build()

# ================= ADMIN CHECK =================
async def is_admin(user_id, chat_id):
    try:
        admins = await application.bot.get_chat_administrators(chat_id)
        return any(a.user.id == user_id for a in admins)
    except:
        return False

# ================= DATE =================
def get_date():
    tz = pytz.timezone("Asia/Riyadh")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M")

# ================= TEXT =================
def get_status_text():
    cursor.execute("SELECT name, status FROM students")
    data = cursor.fetchall()

    cursor.execute("SELECT name FROM banned")
    banned = [r[0] for r in cursor.fetchall()]

    text = "السلام عليكم ورحمة الله وبركاته\n\n"

    cats = {
        "register": "✍️ المسجلات",
        "read": "✅ قرأت",
        "listen": "🎧 مستمعات",
        "excuse": "⛔️ معتذرات"
    }

    for key, title in cats.items():
        text += f"{title}:\n"
        names = [n for n, s in data if s == key]
        text += "\n".join(f"• {n}" for n in names) if names else "لا يوجد"
        text += "\n\n"

    text += "🚫 المحظورات:\n"
    text += "\n".join(f"• {n}" for n in banned) if banned else "لا يوجد"

    text += "\n\n﴿ وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ۚ وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ ﴾\n\n"

    text += "خادم القرآن الرقمي\n"
    text += f"📅 {get_date()}\n"

    return text

# ================= KEYBOARD =================
async def get_keyboard(update):
    kb = [
        [
            InlineKeyboardButton("✍ سجل إسمي", callback_data="register"),
            InlineKeyboardButton("❌ إحذف إسمي", callback_data="remove")
        ],
        [
            InlineKeyboardButton("✅ قرأت", callback_data="read"),
            InlineKeyboardButton("🎧 مستمعات", callback_data="listen")
        ],
        [
            InlineKeyboardButton("⛔️ معتذرات", callback_data="excuse"),
            InlineKeyboardButton("🚫 محظورات", callback_data="banned")
        ]
    ]

    if await is_admin(update.effective_user.id, update.effective_chat.id):
        kb.append([
            InlineKeyboardButton("🔒 قفل/فتح التسجيل", callback_data="toggle"),
            InlineKeyboardButton("🗑 تصفير القائمة", callback_data="clear")
        ])

    return InlineKeyboardMarkup(kb)

# ================= START =================
async def start(update: Update, context):
    await update.message.reply_text(
        get_status_text(),
        reply_markup=await get_keyboard(update)
    )

# ================= LINK FILTER =================
async def link_filter(update: Update, context):
    if update.message and update.message.text:
        if re.search(r"http|www|t\.me", update.message.text):
            if not await is_admin(update.effective_user.id, update.effective_chat.id):
                await update.message.delete()
                await update.message.reply_text(
                    "⛔️⛔️⛔️ إرسال روابط من دون الرجوع للإشراف يعرضك للحذف"
                )

# ================= BAN SYSTEM =================
async def ban_user(update: Update, context):
    msg = update.message

    if not msg.reply_to_message:
        await msg.reply_text("❌ لازم ترد على رسالة الطالبة")
        return

    if not await is_admin(update.effective_user.id, update.effective_chat.id):
        return

    user = msg.reply_to_message.from_user
    name = user.full_name

    cursor.execute("DELETE FROM students WHERE user_id=?",
