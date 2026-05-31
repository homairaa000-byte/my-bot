import os, logging, sqlite3
from datetime import datetime
import pytz
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import threading

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
        conn.execute("CREATE TABLE IF NOT EXISTS users (chat_id INTEGER, user_id INTEGER, name TEXT, status TEXT, is_banned INTEGER DEFAULT 0, read_status INTEGER DEFAULT 0, PRIMARY KEY(chat_id, user_id))")

def fetch(chat_id):
    with db() as conn:
        return conn.execute("SELECT name, status, is_banned, read_status FROM users WHERE chat_id=?", (chat_id,)).fetchall()

def build(chat_id):
    data = fetch(chat_id)
    def f(s, banned=False): 
        res = []
        for n, st, b, rd in data:
            if banned and b == 1: res.append(n)
            elif not banned and st == s:
                # تظهر العلامة فقط للمسجلات (register) اللاتي ضغطن على قرأت
                mark = " ✅" if (rd == 1 and s == 'register') else ""
                res.append(f"{n}{mark}")
        return "لا يوجد" if not res else "\n".join(f"{i+1}- {item}" for i, item in enumerate(res))
    
    now = datetime.now(pytz.timezone("Asia/Riyadh")).strftime("%Y-%m-%d %H:%M")
    return (f"السلام عليكم ورحمة الله وبركاته\n📅 {now}\n\nخادم القرآن الرقمي 💫\nقائمة تسجيل الأدوار 📝\n\n"
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
        if data in ["register", "listener", "excused"]:
            # عند التسجيل الجديد، نضبط الحالة ونصفر علامة الصح
            conn.execute("INSERT OR REPLACE INTO users (chat_id, user_id, name, status, read_status) VALUES (?, ?, ?, ?, 0)", 
                         (chat_id, user_id, q.from_user.full_name, data))
        elif data == "read":
            # التحقق: هل العضوة مسجلة في قائمة المسجلات؟
            user = conn.execute("SELECT status FROM users WHERE chat_id=? AND user_id=?", (chat_id, user_id)).fetchone()
            if user and user[0] == 'register':
                conn.execute("UPDATE users SET read_status = CASE WHEN read_status=0 THEN 1 ELSE 0 END WHERE chat_id=? AND user_id=?", (chat_id, user_id))
            else:
                await q.answer("❌ يجب تسجيل اسمك أولاً في 'المسجلات' لتتمكني من وضع علامة الصح!", show_alert=True)
                return
        elif data == "remove":
            conn.execute("DELETE FROM users WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        elif data == "reset":
            if (await context.bot.get_chat_member(chat_id, q.from_user.id)).status in ['creator', 'administrator']:
                conn.execute("DELETE FROM users WHERE chat_id=?", (chat_id,))
            else: return await q.answer("❌ للمشرفات فقط!", show_alert=True)
    
    await q.edit_message_text(build(chat_id), reply_markup=menu())

# يجب التأكد من ربط الدالة بالـ Handler في الـ main
# app.add_handler(CallbackQueryHandler(buttons))
