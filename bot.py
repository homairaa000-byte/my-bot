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
        conn.execute("CREATE TABLE IF NOT EXISTS users (chat_id INTEGER, user_id INTEGER, name TEXT, status TEXT, is_banned INTEGER DEFAULT 0, PRIMARY KEY(chat_id, user_id))")

# الدوال المنطقية
def set_user(chat_id, user_id, name, status):
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO users (chat_id, user_id, name, status) VALUES (?, ?, ?, ?)", (chat_id, user_id, name, status))

def set_ban(chat_id, user_id, name, ban_status):
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO users (chat_id, user_id, name, status, is_banned) VALUES (?, ?, ?, 'blocked', ?)", (chat_id, user_id, name, ban_status))

def fetch(chat_id):
    with db() as conn:
        return conn.execute("SELECT name, status, is_banned FROM users WHERE chat_id=?", (chat_id,)).fetchall()

def build(chat_id):
    data = fetch(chat_id)
    def f(s, banned=False): 
        res = [n for n, st, b in data if (st == s and not banned) or (b == 1 and banned)]
        return "لا يوجد" if not res else "\n".join(f"{i+1}- {n}" for i, n in enumerate(res))
    
    now = datetime.now(pytz.timezone("Asia/Riyadh")).strftime("%Y-%m-%d %H:%M")
    return (f"السلام عليكم ورحمة الله وبركاته\n📅 {now}\n\n"
            f"خادم القرآن الرقمي 💫\nقائمة تسجيل الأدوار 📝\n\n"
            f"✍️ المسجلات:\n{f('register')}\n\n⛔️ المعتذرات:\n{f('excused')}\n\n"
            f"🎧 المستمعات:\n{f('listener')}\n\n🚫 المحظورات:\n{f('', banned=True)}\n\n"
            f"وَلَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ۚ وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ")

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ سجل اسمي", callback_data="register"), InlineKeyboardButton("✅ قرأت", callback_data="read")],
        [InlineKeyboardButton("🎧 مستمعة", callback_data="listener"), InlineKeyboardButton("⛔️ معتذرة", callback_data="excused")],
        [InlineKeyboardButton("🧹 تصفير", callback_data="reset")],
        [InlineKeyboardButton("❌ حذف اسمي", callback_data="remove")]
    ])

async def is_admin(update):
    try:
        member = await update.effective_chat.get_member(update.effective_user.id)
        return member.status in ['creator', 'administrator']
    except: return False

# الأوامر
async def start(update, context):
    if update.effective_chat.type == 'private':
        await update.message.reply_text("أهلاً بك! هذا البوت مخصص لتنظيم أدوار القرآن. استخدمي الأزرار في المجموعة لتسجيل حضورك.")
    elif await is_admin(update):
        await update.message.reply_text(build(update.effective_chat.id), reply_markup=menu())

async def help_cmd(update, context):
    await update.message.reply_text("وظائف البوت:\n✍️ سجل: لتسجيل اسمك في قائمة القراءة.\n✅ قرأت: لتأكيد إتمامك للقراءة.\n🎧 مستمعة: لتسجيلك كمستمعة.\n⛔️ معتذرة: في حال كان لديك عذر.\n🧹 تصفير: للمشرفات فقط لتصفير القائمة.")

async def ban_user(update, context):
    if not await is_admin(update): return
    target = update.message.reply_to_message
    if target:
        set_ban(update.effective_chat.id, target.from_user.id, target.from_user.full_name, 1)
        await update.message.reply_text("تم حظر العضو من التسجيل.")

async def buttons(update, context):
    q = update.callback_query
    await q.answer()
    chat_id, user_id, data = q.message.chat_id, q.from_user.id, q.data
    
    # التحقق من الحظر
    data_check = fetch(chat_id)
    if any(u[0] == q.from_user.full_name and u[2] == 1 for u in data_check):
        await q.answer("🚫 أنتِ محظورة من التسجيل!", show_alert=True)
        return

    if data in ["register", "listener", "excused", "read"]:
        set_user(chat_id, user_id, q.from_user.full_name, data)
    elif data == "remove":
        # حذف المستخدم من قاعدة البيانات
        with db() as conn:
            conn.execute("DELETE FROM users WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    elif data == "reset":
        if await is_admin(update):
            with db() as conn:
                conn.execute("DELETE FROM users WHERE chat_id=?", (chat_id,))
        else: return await q.answer("❌ للمشرفات فقط!", show_alert=True)

    await q.edit_message_text(build(chat_id), reply_markup=menu())

def main():
    init()
    threading.Thread(target=lambda: app_health.run(host="0.0.0.0", port=PORT), daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CallbackQueryHandler(buttons))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
