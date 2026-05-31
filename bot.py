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
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# إعدادات
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))
DB = "bot.db"

# تهيئة Flask للصحة (لإبقاء الخدمة حية على Render)
app_health = Flask(__name__)
@app_health.route('/')
def health(): return "Bot is live!", 200

# تهيئة البيانات
try:
    r = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=int(os.getenv("REDIS_PORT", 6379)), decode_responses=True)
except: r = None

def db(): return sqlite3.connect(DB, check_same_thread=False)

def init():
    with db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS users (chat_id INTEGER, user_id INTEGER, name TEXT, status TEXT, PRIMARY KEY(chat_id, user_id))")

# الدوال المنطقية
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

# واجهة العرض
def build(chat_id):
    data = fetch(chat_id)
    def g(s): return [n for n, st in data if st == s]
    def f(l): return "لا يوجد" if not l else "\n".join(f"{i+1}- {n}" for i, n in enumerate(l))
    now = datetime.now(pytz.timezone("Africa/Tripoli")).strftime("%Y-%m-%d %H:%M")
    return f"📅 {now}\n\n📖 خادم القرآن الرقمي\n\n✍️ مسجلات:\n{f(g('register'))}\n\n🎧 مستمعات:\n{f(g('listener'))}\n\n⛔️ معتذرات:\n{f(g('excused'))}\n\n✅ قرأت:\n{f(g('read'))}\n\n🚫 محظورات:\n{f(g('blocked'))}"

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ سجل اسمي", callback_data="register"), InlineKeyboardButton("✅ قرأت", callback_data="read")],
        [InlineKeyboardButton("🎧 مستمعة", callback_data="listener"), InlineKeyboardButton("⛔️ معتذرة", callback_data="excused")],
        [InlineKeyboardButton("🔒 قفل/فتح", callback_data="lock"), InlineKeyboardButton("🧹 تصفير", callback_data="reset")],
        [InlineKeyboardButton("❌ حذف اسمي", callback_data="remove")]
    ])

# الأوامر
async def is_admin(update, context):
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        return member.status in ['creator', 'administrator']
    except: return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == 'private':
        await update.message.reply_text("أهلاً بك في خادم القرآن الرقمي! أنا هنا لتنظيم الأدوار. استخدمي الأزرار في المجموعة لتسجيل حضورك.")
    else:
        await update.message.reply_text(build(chat.id), reply_markup=menu())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id, user_id, data = q.message.chat_id, q.from_user.id, q.data
    
    if data in ["register", "listener", "excused", "read", "blocked"]:
        set_user(chat_id, user_id, q.from_user.full_name, data)
    elif data == "remove":
        remove_user(chat_id, user_id)
    elif data == "reset":
        if await is_admin(update, context): reset_chat(chat_id)
        else: return await q.answer("❌ للمشرفات فقط!", show_alert=True)
    elif data == "lock":
        return await q.answer("قريباً.. الميزة تحت التطوير!", show_alert=True)

    await q.edit_message_text(build(chat_id), reply_markup=menu())

def main():
    init()
    # تشغيل Flask كخادم صحة في الخلفية
    threading.Thread(target=lambda: app_health.run(host="0.0.0.0", port=PORT), daemon=True).start()
    
    # تشغيل البوت
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
