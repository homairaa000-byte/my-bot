import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
import sqlite3

# --- الإعدادات ---
TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = "https://my-bot-nquv.onrender.com/webhook"
DB = "/tmp/bot.db"

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# --- تهيئة البوت بدون Loop معقدة ---
bot_app = Application.builder().token(TOKEN).build()

# --- قاعدة البيانات ---
def db(): return sqlite3.connect(DB, check_same_thread=False)

def init():
    with db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS groups (chat_id INTEGER PRIMARY KEY, locked INTEGER DEFAULT 0)")
        conn.execute("CREATE TABLE IF NOT EXISTS users (chat_id INTEGER, user_id INTEGER, name TEXT, status TEXT, is_banned INTEGER DEFAULT 0, read_status INTEGER DEFAULT 0, PRIMARY KEY(chat_id, user_id))")
init()

# --- التنسيقات (تنسيقك الأصلي) ---
def build(chat_id):
    with db() as conn:
        conn.execute("INSERT OR IGNORE INTO groups (chat_id, locked) VALUES (?, 0)", (chat_id,))
        locked = conn.execute("SELECT locked FROM groups WHERE chat_id=?", (chat_id,)).fetchone()
        is_locked = locked[0] if locked else 0
        data = conn.execute("SELECT name, status, is_banned, read_status FROM users WHERE chat_id=?", (chat_id,)).fetchall()
    
    status_text = "🔒 التسجيل مغلق" if is_locked else "🔓 التسجيل مفتوح"
    
    def f(s, banned=False): 
        res = []
        for n, st, b, rd in data:
            if banned and b == 1: res.append(n)
            elif not banned and st == s:
                mark = " ✅" if (rd == 1 and s == 'register') else ""
                res.append(f"{n}{mark}")
        return "لا يوجد" if not res else "\n".join(f"{i+1}- {item}" for i, item in enumerate(res))
    
    return (f"السلام عليكم ورحمة الله وبركاته\n\nخادم القرآن الرقمي 💫\n{status_text}\nقائمة تسجيل الأدوار 📝\n\n"
            f"✍️ المسجلات:\n{f('register')}\n\n⛔️ المعتذرات:\n{f('excused')}\n\n"
            f"🎧 المستمعات:\n{f('listener')}\n\n🚫 المحظورات:\n{f('', banned=True)}\n\n"
            f"وَلَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ۚ وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ")

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ قرأت", callback_data="read"), InlineKeyboardButton("✍️ سجل اسمي", callback_data="register")],
        [InlineKeyboardButton("🎧 مستمعة", callback_data="listener"), InlineKeyboardButton("⛔️ معتذرة", callback_data="excused")],
        [InlineKeyboardButton("🧹 تصفير", callback_data="reset"), InlineKeyboardButton("🔒 قفل/فتح", callback_data="lock")],
        [InlineKeyboardButton("❌ حذف اسمي", callback_data="remove")]
    ])

# --- المعالجات ---
async def start(update, context):
    await update.message.reply_text(build(update.effective_chat.id), reply_markup=menu())

async def buttons(update, context):
    q = update.callback_query
    await q.answer()
    chat_id, user_id = q.message.chat_id, q.from_user.id
    data = q.data
    with db() as conn:
        if data in ["register", "listener", "excused"]:
            conn.execute("INSERT OR REPLACE INTO users (chat_id, user_id, name, status, read_status) VALUES (?, ?, ?, ?, 0)", (chat_id, user_id, q.from_user.full_name, data))
        elif data == "lock":
            conn.execute("UPDATE groups SET locked = CASE WHEN locked=0 THEN 1 ELSE 0 END WHERE chat_id=?", (chat_id,))
        elif data == "remove": conn.execute("DELETE FROM users WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        elif data == "reset": conn.execute("DELETE FROM users WHERE chat_id=?", (chat_id,))
        elif data == "read": conn.execute("UPDATE users SET read_status = 1 WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    await q.edit_message_text(build(chat_id), reply_markup=menu())

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CallbackQueryHandler(buttons))

# --- تشغيل البوت مع Flask ---
@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    asyncio.run(bot_app.process_update(update))
    return "ok", 200

@app.route('/')
def index(): return "Bot is running", 200

# تهيئة البوت عند بدء التشغيل
asyncio.run(bot_app.initialize())
asyncio.run(bot_app.bot.set_webhook(WEBHOOK_URL))
