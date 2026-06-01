import os
import logging
import sqlite3
import threading
import asyncio
import pytz
from datetime import datetime
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from apscheduler.schedulers.background import BackgroundScheduler

# --- الإعدادات ---
TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))
DB = "bot.db"

logging.basicConfig(level=logging.INFO)

app_health = Flask(__name__)
@app_health.route('/')
def health(): return "Bot is live", 200

def db(): return sqlite3.connect(DB, check_same_thread=False)

def init():
    with db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS groups (chat_id INTEGER PRIMARY KEY, locked INTEGER DEFAULT 0)")
        conn.execute("CREATE TABLE IF NOT EXISTS users (chat_id INTEGER, user_id INTEGER, name TEXT, status TEXT, is_banned INTEGER DEFAULT 0, read_status INTEGER DEFAULT 0, PRIMARY KEY(chat_id, user_id))")

# --- المهام التلقائية مع الرسائل ---
async def send_notification(application, text):
    with db() as conn:
        chats = conn.execute("SELECT chat_id FROM groups").fetchall()
    for (chat_id,) in chats:
        try:
            await application.bot.send_message(chat_id=chat_id, text=text)
        except Exception as e:
            logging.error(f"فشل إرسال التنبيه لـ {chat_id}: {e}")

async def auto_toggle_lock(application, lock_status):
    with db() as conn:
        conn.execute("UPDATE groups SET locked = ?", (lock_status,))
    
    if lock_status == 1:
        message = "أمسينا وأمسى الملك لله 🔐 تم قفل المجموعة"
    else:
        message = "أصبحنا وأصبح الملك لله 🔓 تم فتح المجموعة"
        
    await send_notification(application, message)

def setup_scheduler(application):
    scheduler = BackgroundScheduler(timezone=pytz.timezone("Asia/Riyadh"))
    # القفل الساعة 12 منتصف الليل
    scheduler.add_job(lambda: asyncio.run_coroutine_threadsafe(auto_toggle_lock(application, 1), application.loop), 'cron', hour=0, minute=0)
    # الفتح الساعة 8 صباحاً
    scheduler.add_job(lambda: asyncio.run_coroutine_threadsafe(auto_toggle_lock(application, 0), application.loop), 'cron', hour=8, minute=0)
    scheduler.start()

# --- واجهة البوت ---
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
    
    now = datetime.now(pytz.timezone("Asia/Riyadh")).strftime("%Y-%m-%d %H:%M")
    return (f"السلام عليكم ورحمة الله وبركاته\n📅 {now}\n\nخادم القرآن الرقمي 💫\n{status_text}\nقائمة تسجيل الأدوار 📝\n\n"
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

async def buttons(update, context):
    q = update.callback_query
    await q.answer()
    chat_id, user_id = q.message.chat_id, q.from_user.id
    data = q.data
    with db() as conn:
        locked = conn.execute("SELECT locked FROM groups WHERE chat_id=?", (chat_id,)).fetchone()
        is_locked = locked[0] if locked else 0
        
        is_banned = conn.execute("SELECT is_banned FROM users WHERE chat_id=? AND user_id=?", (chat_id, user_id)).fetchone()
        if is_banned and is_banned[0] == 1:
            await q.answer("❌ أنت محظورة ولا يمكنك التفاعل!", show_alert=True); return

        if data in ["register", "listener", "excused"]:
            if is_locked:
                await q.answer("❌ التسجيل مغلق حالياً!", show_alert=True); return
            conn.execute("INSERT OR REPLACE INTO users (chat_id, user_id, name, status, read_status) VALUES (?, ?, ?, ?, COALESCE((SELECT read_status FROM users WHERE chat_id=? AND user_id=?), 0))", (chat_id, user_id, q.from_user.full_name, data, chat_id, user_id))
        elif data == "lock":
            if (await context.bot.get_chat_member(chat_id, user_id)).status in ['creator', 'administrator']:
                conn.execute("UPDATE groups SET locked = CASE WHEN locked=0 THEN 1 ELSE 0 END WHERE chat_id=?", (chat_id,))
            else: await q.answer("❌ للمشرفات فقط!", show_alert=True)
        elif data == "read":
            user = conn.execute("SELECT status FROM users WHERE chat_id=? AND user_id=?", (chat_id, user_id)).fetchone()
            if user and user[0] == 'register':
                conn.execute("UPDATE users SET read_status = CASE WHEN read_status=0 THEN 1 ELSE 0 END WHERE chat_id=? AND user_id=?", (chat_id, user_id))
            else: await q.answer("❌ سجل اسمك أولاً كمسجلة!", show_alert=True); return
        elif data == "remove": conn.execute("DELETE FROM users WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        elif data == "reset":
            if (await context.bot.get_chat_member(chat_id, user_id)).status in ['creator', 'administrator']:
                conn.execute("DELETE FROM users WHERE chat_id=?", (chat_id,))
            else: await q.answer("❌ للمشرفات فقط!", show_alert=True); return
    await q.edit_message_text(build(chat_id), reply_markup=menu())

async def start(update, context):
    init()
    await update.message.reply_text(build(update.effective_chat.id), reply_markup=menu())

async def ban_user(update, context):
    if (await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)).status in ['creator', 'administrator']:
        if update.message.reply_to_message:
            u_id = update.message.reply_to_message.from_user.id
            with db() as conn: conn.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (u_id,))
            await update.message.reply_text("⛔️ تم حظر العضوة.")

def main():
    if not TOKEN: return
    application = Application.builder().token(TOKEN).build()
    
    setup_scheduler(application) # تفعيل المجدول
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ban", ban_user))
    application.add_handler(CallbackQueryHandler(buttons))
    
    def run_flask(): app_health.run(host="0.0.0.0", port=PORT)
    threading.Thread(target=run_flask, daemon=True).start()
    
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__': 
    init()
    main()
