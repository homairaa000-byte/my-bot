import os
import time
import sqlite3
import threading
from datetime import datetime
from flask import Flask, request
import telebot

# =========================
# SETTINGS
# =========================

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# =========================
# DATABASE
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
# TEXTS (FULL)
# =========================

WARNING_MESSAGE = "عذراً، الأكاديمية مخصصة للنساء فقط."

WELCOME_MESSAGE = """
مرحبا مرحبا بوصية رسول الله...
قال رسول الله ﷺ: "سيأتيكُم أقوامٌ يطلبونَ العِلمَ..."
أهلاً بكِ في الأكاديمية 🕊🌴
"""

SCHEDULE_TEXT = """
✍ جدول الحلقات

💐 المعلمة : لطيفة تصحيح تلاوة
📝 المشرفة : دنيا
⏰ التوقيت : الاثنين 12 مكة

💐 المعلمة : عالية محمد
📝 المشرفة : ساجدة
⏰ التوقيت : 6 مساءً
"""

RULES_TEXT = """
📜 قوانين الأكاديمية:

1. الأكاديمية للنساء فقط 🚫
2. الالتزام مطلوب
3. ممنوع الروابط
4. ممنوع الخاص
"""

HELP_TEXT = """
📌 الأوامر:
/start
/rules
/schedule
/help
"""

# =========================
# MENU (REGISTER SYSTEM)
# =========================

def menu():
    return telebot.types.InlineKeyboardMarkup(row_width=2).add(
        telebot.types.InlineKeyboardButton("✍ سجل اسمي", callback_data="register"),
        telebot.types.InlineKeyboardButton("🎧 مستمعة", callback_data="listener"),
        telebot.types.InlineKeyboardButton("⛔ معتذرة", callback_data="excused"),
        telebot.types.InlineKeyboardButton("❌ حذف اسمي", callback_data="remove"),
        telebot.types.InlineKeyboardButton("🧹 تصفير", callback_data="reset")
    )

# =========================
# BUILD LIST
# =========================

def build(chat_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT name,status FROM users WHERE chat_id=?", (chat_id,))
    data = c.fetchall()
    conn.close()

    def section(status):
        return "\n".join([d[0] for d in data if d[1] == status]) or "لا يوجد"

    return f"""
📅 قائمة التسجيل

✍ المسجلات:
{section('register')}

🎧 المستمعات:
{section('listener')}

⛔ المعتذرات:
{section('excused')}
"""

# =========================
# FLASK
# =========================

@app.route("/")
def home():
    return "BOT RUNNING"

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK"

# =========================
# START MESSAGE
# =========================

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, build(message.chat.id), reply_markup=menu())

# =========================
# RULES / HELP / SCHEDULE
# =========================

@bot.message_handler(commands=['rules'])
def rules(message):
    bot.send_message(message.chat.id, RULES_TEXT)

@bot.message_handler(commands=['schedule'])
def schedule(message):
    bot.send_message(message.chat.id, SCHEDULE_TEXT)

@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.send_message(message.chat.id, HELP_TEXT)

# =========================
# JOIN WELCOME (DELETE AFTER 5 MIN)
# =========================

@bot.message_handler(content_types=["new_chat_members"])
def welcome(message):
    sent = bot.send_message(
        message.chat.id,
        f"🌸 أهلاً بكِ {message.new_chat_members[0].first_name}\n\n{WELCOME_MESSAGE}"
    )

    def delete_later(chat_id, msg_id):
        time.sleep(300)
        try:
            bot.delete_message(chat_id, msg_id)
        except:
            pass

    threading.Thread(
        target=delete_later,
        args=(message.chat.id, sent.message_id)
    ).start()

# =========================
# CALLBACKS
# =========================

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    name = call.from_user.first_name
    action = call.data

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    if action in ["register", "listener", "excused"]:
        c.execute("""
        INSERT OR REPLACE INTO users(chat_id,user_id,name,status,created_at)
        VALUES(?,?,?,?,?)
        """, (chat_id, user_id, name, action, datetime.now()))

    elif action == "remove":
        c.execute("DELETE FROM users WHERE chat_id=? AND user_id=?", (chat_id, user_id))

    elif action == "reset":
        c.execute("DELETE FROM users WHERE chat_id=?", (chat_id,))

    conn.commit()
    conn.close()

    bot.edit_message_text(
        build(chat_id),
        chat_id,
        call.message.message_id,
        reply_markup=menu()
    )

# =========================
# RUN WEBHOOK
# =========================

if __name__ == "__main__":
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")

    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
