import os
import time
import logging
import sqlite3
import redis
import threading
from datetime import datetime
import pytz
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# =========================
# إعدادات
# =========================
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))
DB = "bot.db"

# =========================
# تهيئة Redis و SQLite
# =========================
try:
    r = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=int(os.getenv("REDIS_PORT", 6379)), decode_responses=True)
except:
    r = None

def db(): return sqlite3.connect(DB, check_same_thread=False)

def init():
    with db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS users (chat_id INTEGER, user_id INTEGER, name TEXT, status TEXT, PRIMARY KEY(chat_id, user_id))")

# =========================
# الدوال المنطقية
# =========================
def is_spam(user_id):
    if not r: return False
    key = f"spam:{user_id}"
    last = r.get(key)
    now = time.time()
    r.set(key, now)
    return last and now - float(last) < 2

def set_user(chat_id, user_id, name, status):
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)", (chat_id, user_id, name, status))

def remove_user(chat_id, user_id):
    with db() as conn:
        conn.execute("DELETE FROM users WHERE chat_id=? AND user_id=?", (chat_id, user_id))

def reset_chat(chat_id):
    with db() as conn:
        conn.execute("DELETE FROM users WHERE chat_id=?", (chat_id,))

def fetch(chat_id):
    with db() as conn:
        return conn.execute("SELECT name, status FROM users WHERE chat_id=?", (chat_id,)).fetchall()

# =========================
# واجهة العرض (UI)
# =========================
def build(chat_id):
    data = fetch(chat_id)
    def g(s): return [n for n, st in data if st == s]
    def f(l): return "لا يوجد" if not l else "\n".join(f"{i+1}- {n}" for i, n in enumerate(l))
    now = datetime.now(pytz.timezone("Africa/Tripoli")).strftime("%Y-%m-%d %H:%M")
    return f"📅 {now}\n\n📖 خادم القرآن الرقمي\n\n✍️ مسجلات:\n{f(g('register'))}\n\n🎧 مستمعات:\n{f(g('listener'))}\n\n⛔️ معتذرات:\n{f(g('excused'))}\n\n✅ قرأت:\n{f(g('read'))}"

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ سجل", callback_data="register"), InlineKeyboardButton("🎧 مستمعة", callback_data="listener")],
        [InlineKeyboardButton("⛔️ معتذرة", callback_data="excused"), InlineKeyboardButton("✅ قرأت", callback_data="read")],
        [InlineKeyboardButton("🧹 تصفير", callback_data="reset"), InlineKeyboardButton("❌ حذف", callback_data="remove")]
    ])

# =========================
# الصلاحيات والأوامر
# =========================
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private': return False
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        return member.status in ['creator', 'administrator']
    except: return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(build(update.effective_chat.id), reply_markup=menu())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if is_spam(q.from_user.id):
        await q.answer("⚠️ ببطء من فضلك!", show_alert=True)
        return
    await q.answer()
    
    chat_id, user_id, data = q.message.chat_id, q.from_user.id, q.data
    
    if data in ["register", "listener", "excused", "read"]:
        set_user(chat_id, user_id, q.from_user.full_name, data)
    elif data == "remove":
        remove_user(chat_id, user_id)
    elif data == "reset":
        if await is_admin(update, context):
            reset_chat(chat_id)
        else:
            await q.answer("❌ هذا الأمر للمشرفات فقط!", show_alert=True)
            return

    await q.edit_message_text(build(chat_id), reply_markup=menu())

# =========================
# التشغيل (Main)
# =========================
app_health = Flask(__name__)
@app_health.route('/')
def health(): return "Bot is live", 200

def main():
    init()
    threading.Thread(target=lambda: app_health.run(host="0.0.0.0", port=PORT), daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
