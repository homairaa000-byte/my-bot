import os
import telebot
import threading
import time
import re
import schedule
from flask import Flask, request
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# =========================
# إعداد البوت
# =========================
TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
DATABASE_URL = os.environ.get("DATABASE_URL")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# =========================
# قاعدة البيانات (SYNC فقط)
# =========================
def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# =========================
# النصوص (بدون أي تعديل)
# =========================
WELCOME_MESSAGE = """
السلام عليكم ورحمة الله وبركاته
📅 تم التحديث: {date}

مرحبا مرحبا بوصية رسول الله...
قال رسول الله ﷺ: "سيأتيكُم أقوامٌ يطلبونَ العِلمَ، فإذا رأيتُموهم فقولوا لَهُم: مَرحبًا مَرحبًا بوصيَّةِ رسولِ اللَّهِ صلَّى اللَّهَ عليهِ وسلَّمَ، واقْنوهُم". قلتُ للحَكَمِ: ما اقْنوهُم؟ قالَ: علِّموهُم.

أهلاً بكِ في أكاديمية معارج الإتقان 🕊🌴🌴🌴
يرجى قراءة قوانين الأكاديمية المثبتة والالتزام بها.
"""

RULES_TEXT = """
بسم الله الرحمن الرحيم 

أكاديمية معارج الاتقان 🕊🌴🌴🌴

قوانين الأكاديمية:

🌴🌴الأكاديمية تعنى بتقديم كل ما يتعلق بالتجويد والقران من حصص تجويد وتصحيح تلاوه وقراءات وغيرها من المجالات. 

1. الأكاديمية خاصه بالنساء فقط، يمنع منعاً باتاً انضمام الرجال.🚫🚫🚫
2. ليس هنالك شروط للإنضمام سوى الإنضباط.👩‍✈️👩‍✈️
3. الرجاء كتابه الاسم بوضوح وعدم استخدام الرموز.❌❌
4. ممنوع نشر الروابط. 🛑🛑🛑
5. ممنوع التواصل الخاص.✋✋
"""

SCHEDULE_TEXT = """
✍جدول حلقات المقرأة♕

(هنا الجدول كامل كما هو بدون تغيير)
"""

HELP_TEXT = """
🌸 **قائمة أوامر مساعد أكاديمية معارج الإتقان** 🌸

📌 /rules
📌 /schedule
📌 /help
"""

# =========================
# DB FUNCTIONS
# =========================
def add_user(chat_id, user_id, name, status):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (chat_id,user_id,name,status,read_status,created_at)
        VALUES (%s,%s,%s,%s,FALSE,%s)
        ON CONFLICT (chat_id,user_id)
        DO UPDATE SET status=%s, created_at=%s
    """, (chat_id, user_id, name, status, datetime.now(), status, datetime.now()))
    conn.commit()
    conn.close()

def toggle_lock(chat_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT locked FROM groups WHERE chat_id=%s", (chat_id,))
    row = cur.fetchone()

    if not row:
        locked = False
        cur.execute("INSERT INTO groups(chat_id,locked) VALUES(%s,FALSE)", (chat_id,))
    else:
        locked = not row["locked"]
        cur.execute("UPDATE groups SET locked=%s WHERE chat_id=%s", (locked, chat_id))

    conn.commit()
    conn.close()
    return locked

def build(chat_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT name,status,read_status FROM users WHERE chat_id=%s ORDER BY created_at ASC", (chat_id,))
    data = cur.fetchall()

    cur.execute("SELECT locked FROM groups WHERE chat_id=%s", (chat_id,))
    row = cur.fetchone()
    locked = row["locked"] if row else False

    conn.close()

    status_text = "🔒 التسجيل مغلق" if locked else "🔓 التسجيل مفتوح"
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def section(status):
        result = [f"{r['name']}{' ✅' if r['read_status'] else ''}" for r in data if r['status'] == status]
        return "\n".join(f"{i+1}- {x}" for i, x in enumerate(result)) if result else "لا يوجد"

    return (
        "السلام عليكم ورحمة الله وبركاته\n"
        f"📅 {date_str}\n\n"
        "خادم القرآن الرقمي 💫\n"
        f"{status_text}\n\n"
        "📋 قائمة التسجيل:\n\n"
        f"✍️ المسجلات:\n{section('register')}\n\n"
        f"⛔️ المعتذرات:\n{section('excused')}\n\n"
        f"🎧 المستمعات:\n{section('listener')}\n\n"
        f"🚫 المحظورات:\n{section('banned')}\n\n"
        "﴿وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ۚ وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ﴾"
    )

# =========================
# MENU (بدون تغيير)
# =========================
def menu():
    return telebot.types.InlineKeyboardMarkup([
        [
            telebot.types.InlineKeyboardButton("✅ قرأت", callback_data="read"),
            telebot.types.InlineKeyboardButton("✍️ سجل اسمي", callback_data="register")
        ],
        [
            telebot.types.InlineKeyboardButton("🎧 مستمعة", callback_data="listener"),
            telebot.types.InlineKeyboardButton("⛔️ معتذرة", callback_data="excused")
        ],
        [
            telebot.types.InlineKeyboardButton("🔒 قفل/فتح", callback_data="lock"),
            telebot.types.InlineKeyboardButton("❌ حذف اسمي", callback_data="remove")
        ],
        [
            telebot.types.InlineKeyboardButton("🧹 تصفير القائمة", callback_data="reset")
        ]
    ])

# =========================
# HANDLERS
# =========================
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        WELCOME_MESSAGE.format(date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        reply_markup=menu()
    )

@bot.message_handler(commands=['rules'])
def rules(message):
    bot.send_message(message.chat.id, RULES_TEXT)

@bot.message_handler(commands=['schedule'])
def schedule_cmd(message):
    bot.send_message(message.chat.id, SCHEDULE_TEXT)

@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.send_message(message.chat.id, HELP_TEXT, parse_mode="Markdown")

# =========================
# CALLBACKS
# =========================
@bot.callback_query_handler(func=lambda q: True)
def callbacks(q):
    chat_id = q.message.chat.id
    user_id = q.from_user.id
    action = q.data

    if action == "lock":
        locked = toggle_lock(chat_id)

        bot.set_chat_permissions(chat_id, telebot.types.ChatPermissions(
            can_send_messages=not locked,
            can_send_media_messages=not locked,
            can_send_polls=not locked,
            can_send_other_messages=not locked
        ))

    elif action == "reset":
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE chat_id=%s AND status!='banned'", (chat_id,))
        conn.commit()
        conn.close()

    elif action == "remove":
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE chat_id=%s AND user_id=%s", (chat_id, user_id))
        conn.commit()
        conn.close()

    elif action == "read":
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            UPDATE users SET read_status = NOT read_status
            WHERE chat_id=%s AND user_id=%s
        """, (chat_id, user_id))
        conn.commit()
        conn.close()

    else:
        add_user(chat_id, user_id, q.from_user.full_name, action)

    new_text = build(chat_id)

    bot.edit_message_text(
        chat_id=chat_id,
        message_id=q.message.message_id,
        text=new_text,
        reply_markup=menu()
    )

# =========================
# WEBHOOK FLASK
# =========================
@app.route('/', methods=['GET'])
def home():
    return "OK", 200

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
    bot.process_new_updates([update])
    return "", 200

# =========================
# تشغيل
# =========================
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL.rstrip('/')}/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
