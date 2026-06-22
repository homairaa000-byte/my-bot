import os
import sqlite3
import threading
import time
import re
import schedule
import logging
from datetime import datetime
from flask import Flask, request

import telebot
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# =========================
# SETTINGS
# =========================

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

logging.basicConfig(level=logging.INFO)

# =========================
# SQLITE
# =========================

DB = "bot.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        chat_id INTEGER,
        user_id INTEGER,
        name TEXT,
        status TEXT,
        read_status INTEGER DEFAULT 0,
        created_at TEXT,
        PRIMARY KEY (chat_id, user_id)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS groups (
        chat_id INTEGER PRIMARY KEY,
        locked INTEGER DEFAULT 0
    )
    """)

    conn.commit()
    conn.close()

init_db()

# =========================
# BOT 1 (نظام التسجيل)
# =========================

bot_app = Application.builder().token(TOKEN).build()

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except:
        return False

def get_locked(chat_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("INSERT OR IGNORE INTO groups(chat_id,locked) VALUES(?,0)", (chat_id,))
    conn.commit()

    c.execute("SELECT locked FROM groups WHERE chat_id=?", (chat_id,))
    row = c.fetchone()
    conn.close()

    return row[0] if row else 0

# =========================
# 📌 قائمة التسجيل (مكملة بالكامل)
# =========================

def build(chat_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    locked = get_locked(chat_id)

    c.execute("SELECT name,status,read_status FROM users WHERE chat_id=?", (chat_id,))
    data = c.fetchall()
    conn.close()

    status_text = "🔒 التسجيل مغلق" if locked else "🔓 التسجيل مفتوح"
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def section(status):
        result = [f"{r[0]}{' ✅' if r[2] else ''}" for r in data if r[1] == status]
        return "\n".join(result) if result else "لا يوجد"

    return (
        "السلام عليكم ورحمة الله وبركاته\n"
        f"📅 {date_str}\n\n"
        "خادم القرآن الرقمي 💫\n"
        f"{status_text}\n"
        "قائمة تسجيل الأدوار 📝\n\n"
        f"✍️ المسجلات:\n{section('register')}\n\n"
        f"⛔️ المعتذرات:\n{section('excused')}\n\n"
        f"🎧 المستمعات:\n{section('listener')}\n\n"
        f"🚫 المحظورات:\n{section('banned')}\n\n"
        "وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ۚ وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ"
    )

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ قرأت", callback_data="read"),
         InlineKeyboardButton("✍️ سجل اسمي", callback_data="register")],
        [InlineKeyboardButton("🎧 مستمعة", callback_data="listener"),
         InlineKeyboardButton("⛔️ معتذرة", callback_data="excused")],
        [InlineKeyboardButton("🔒 قفل/فتح", callback_data="lock"),
         InlineKeyboardButton("❌ حذف اسمي", callback_data="remove")],
        [InlineKeyboardButton("🧹 تصفير القائمة", callback_data="reset")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    await update.message.reply_text(build(update.effective_chat.id), reply_markup=menu())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    chat_id = q.message.chat_id
    user_id = q.from_user.id
    action = q.data

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    if action in ["register", "listener", "excused"]:
        c.execute("""
        INSERT OR REPLACE INTO users(chat_id,user_id,name,status,read_status,created_at)
        VALUES(?,?,?,?,0,?)
        """, (chat_id, user_id, q.from_user.full_name, action, datetime.now()))

    elif action == "read":
        c.execute("""
        UPDATE users SET read_status = 1-read_status
        WHERE chat_id=? AND user_id=?
        """, (chat_id, user_id))

    elif action == "remove":
        c.execute("DELETE FROM users WHERE chat_id=? AND user_id=?", (chat_id, user_id))

    conn.commit()
    conn.close()

    try:
        await q.edit_message_text(build(chat_id), reply_markup=menu())
    except:
        pass

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CallbackQueryHandler(buttons))

# =========================
# BOT 2 (النصوص كاملة بدون أي حذف)
# =========================

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# =========================
# 🔥 النصوص كاملة 100%
# =========================

WARNING_MESSAGE = "عذراً أختي الكريمة، الأكاديمية مخصصة للنساء فقط، يرجى التأكد من أن الاسم صريح وواضح (بدون رموز أو حرف واحد)."

WELCOME_MESSAGE = """
مرحبا مرحبا بوصية رسول الله...
قال رسول الله ﷺ: "سيأتيكُم أقوامٌ يطلبونَ العِلمَ، فإذا رأيتُموهم فقولوا لَهُم: مَرحبًا مَرحبًا بوصيَّةِ رسولِ اللَّهِ صلَّى اللَّهُ عليهِ وسلَّمَ، واقْنوهُم". قلتُ للحَكَمِ: ما اقْنوهُم؟ قالَ: علِّموهُم.

أهلاً بكِ في أكاديمية معارج الإتقان 🕊🌴🌴🌴
يرجى قراءة قوانين الأكاديمية المثبتة والالتزام بها.
"""

# =========================
# 📚 الجدول (بدون تكرار - كامل)
# =========================

SCHEDULE_TEXT = """
" ✍جدول حلقات المقرأة♕

꧁꧁꧁꧁꧂꧂꧂꧂

💐 المعلمة : لطيفة تصحيح تلاوة
📝 المشرفة : دنيا
⏰ التوقيت : الأثنين 12مكة
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : لطيفة المخارج
📝 المشرفة : دنيا
⏰ التوقيت : الثلاثاء 12مكة 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : لطيفة
📝 المشرفة : ..دنيا.
⏰ التوقيت : الأربعاء تأهيل المعلمات 12مكة
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : لطيفة ربع يس 
📝 المشرفة : احلام وليلي
⏰ التوقيت : الخميس 12 مكة 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : منى الدسوقي أصول ورش 
📝 المشرفة : لطيفة
⏰ التوقيت : الأثنين والاربعاء الخامسة مكة
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : عالية محمد (تصحيح تلاوة جزء عم) 
📝 المشرفة : ساجدة علي
⏰ التوقيت : 6:00 م بتوقيت مكة.. 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : إيمان عجلان ﴿تصحيح جزء عم ﴾حفص
📝 المشرفة : ----
⏰ التوقيت : السبت 10.00صباحا توقيت مكه
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : يسر أم عبد الرحمن (تصحيح جزء تبارك)
📝 المشرفة : متى يوسفي
⏰ التوقيت : 10مساءا توقيت مكة
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : أميرة عزت 
شرح احكام النون الساكنه والتنوين 
📝 المشرفة : دنيا
⏰ التوقيت : الاحد 3عصرا بتوقيت مكه 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : مريم ياسين 
📝 المشرفة : 
⏰ التوقيت : الثالثة مساءا بتوقيت ليبيا
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : عائشة عبدالسلام ( حفظ سوره البقرة برواية قالون ) 
📝 المشرفة : ليلي القطروني... ام سومه(هاجر محمد علي) 
⏰ التوقيت :الثلاثاء..الثالثة مساء 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : نهى السعيد(حفظ ربع يس برواية حفص ) 
📝 المشرفة : ليلى القطرونى -عائشة عبد السلام
⏰ التوقيت : السبت -2ظهرا بتوقيت مصر 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : أم ساجدة 
📝 المشرفة : ساجدة 
⏰ التوقيت : العاشرة صباحا بتوقيت ليبيا 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : نسمه طه تصحيح جزئى تبارك وعم 
📝 المشرفة : 
⏰ التوقيت : الخميس ٤م توقيت مصر 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : فاطمه فتحي 
حفظ جزئى تبارك وعم بروايه حفص
📝 المشرفة : ؟؟
⏰ التوقيت : الثلاثاء العاشرة صباحا
❀❀❀❀❀❀❀❀❀❀❀

القرآن في الدنيا نافع🍃
وفي القبر شافع🍃
وفي الجنة رافع🍃
اللهم اجعلنا من أهله وخاصته🤲🌹
"""

# =========================
# 📜 القوانين (كاملة)
# =========================

RULES_TEXT = """
بسم الله الرحمن الرحيم 

أكاديمية معارج الاتقان 🕊🌴🌴🌴

قوانين الأكاديمية:

🌴🌴الأكاديمية تعنى بتقديم كل ما يتعلق بالتجويد والقران من حصص تجويد وتصحيح تلاوه وقراءات وغيرها من المجالات. 

1. الأكاديمية خاصه بالنساء فقط، يمنع منعاً باتاً انضمام الرجال.🚫🚫🚫

2. ليس هنالك شروط للإنضمام للأكاديمية سوى الإنضباط.👩‍✈️👩‍✈️

3. الرجاء كتابه الاسم بوضوح وعدم استخدام الرموز.❌❌

4. مجموعات الحفظ بروايه قالون و حفص تعمل حسب الجداول.

5. ممنوع نشر الروابط.

6. ممنوع التواصل الخاص.

💐 شاكرين حسن تعاونكن 🤍
"""

# =========================
# HELP
# =========================

HELP_TEXT = """
🌸 قائمة أوامر مساعد الأكاديمية 🌸

📌 /rules
📌 /schedule
📌 /help
"""

# =========================
# WEBHOOK + HANDLERS
# =========================

@app.route("/")
def home():
    return "OK"

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK"

@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.send_message(message.chat.id, "🌸 أهلاً بكِ في الأكاديمية 🌸")

@bot.message_handler(commands=['schedule'])
def schedule_cmd(message):
    bot.send_message(message.chat.id, SCHEDULE_TEXT)

@bot.message_handler(commands=['rules'])
def rules_cmd(message):
    bot.send_message(message.chat.id, RULES_TEXT)

@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.send_message(message.chat.id, HELP_TEXT)

@bot.message_handler(content_types=["new_chat_members"])
def welcome(message):
    for u in message.new_chat_members:
        bot.send_message(message.chat.id, f"أهلاً بكِ {u.first_name}\n\n{WELCOME_MESSAGE}")

# =========================
# RUN
# =========================

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
