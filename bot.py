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

# =========================
# SETTINGS
# =========================

TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

# =========================
# DATABASE (SQLite)
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
# النصوص (كما هي 100%)
# =========================

WARNING_MESSAGE = "عذراً أختي الكريمة، الأكاديمية مخصصة للنساء فقط، يرجى التأكد من أن الاسم صريح وواضح (بدون رموز أو حرف واحد)."

WELCOME_MESSAGE = """
مرحبا مرحبا بوصية رسول الله...
قال رسول الله ﷺ: "سيأتيكُم أقوامٌ يطلبونَ العِلمَ، فإذا رأيتُموهم فقولوا لَهُم: مَرحبًا مَرحبًا بوصيَّةِ رسولِ اللَّهِ صلَّى اللَّهُ عليهِ وسلَّمَ، واقْنوهُم". قلتُ للحَكَمِ: ما اقْنوهُم؟ قالَ: علِّموهُم.

أهلاً بكِ في أكاديمية معارج الإتقان 🕊🌴🌴🌴
يرجى قراءة قوانين الأكاديمية المثبتة والالتزام بها.
"""

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
📝 المشرفة :؟؟ 
⏰ التوقيت : تسميع الثلاثاء العاشره 🌤صباحا توقيت مكه ومصر 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : ميمونة تصحيح تلاوة 
📝 المشرفة : زهراء اماني
⏰ التوقيت : يوم الاحد الساعة 2 توقيت مكة 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : تاهيل معلمات
📝 المشرفة : 
⏰ التوقيت : الاثنين 2 توقيت مكة 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : زهراء 
📝 المشرفة : اماني علي 
📆 اليوم: السبت 
⏰ التوقيت : 5 بتوقيت مصر 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : نسرين بركات 
📝 المشرفة : ميمونة 
📆 اليوم: السبت 
⏰ التوقيت : 3 مساء بتوقيت مصر 
❀❀❀❀❀❀❀❀❀❀❀

القرآن في الدنيا نافع🍃
وفي القبر شافع🍃
وفي الجنة رافع🍃
اللهم اجعلنا من أهله وخاصته🤲🌹
"""

RULES_TEXT = """
بسم الله الرحمن الرحيم 

أكاديمية معارج الاتقان 🕊🌴🌴🌴

قوانين الأكاديمية:

🌴🌴الأكاديمية تعنى بتقديم كل ما يتعلق بالتجويد والقران من حصص تجويد وتصحيح تلاوه وقراءات وغيرها من المجالات. 

1. الأكاديمية خاصه بالنساء فقط، يمنع منعاً باتاً انضمام الرجال.🚫🚫🚫

2. ليس هنالك شروط للإنضمام للأكاديمية سوى الإنضباط.👩‍✈️👩‍✈️

3. الرجاء كتابه الاسم بوضوح وعدم استخدام الرموز (والاولاد بدون كلمة أم) حتى لا يتم ازالتك.❌❌

4. مجموعات الحفظ بروايه قالون: ربع يس تحت إشراف المعلمة أم ساجدة، و ربع البقرة تحت اشراف المعلمة مريم، و جزء عم و تبارك تحت إشراف المعلمه يسر ورغي.

5. مجموعات الحفظ برواية حفص: ربع يس تحت إشراف المعلمة نهى سعيد، و ليلى القطروني، جزئي تبارك و عم تحت اشراف المعلمة فاطمة فتحي.

6. ليس لدينا مجموعات حفظ برواية ورش بعد.

7. ممنوع نشر الروابط غير المتعلقة بالأكاديمية.

8. ممنوع التواصل مع المعلمات في الخاص.

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
# GROUP STORAGE
# =========================

def save_group(chat_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO groups(chat_id,locked) VALUES(?,0)", (chat_id,))
    conn.commit()
    conn.close()

# =========================
# WELCOME DELETE AFTER 5 MIN
# =========================

def auto_delete(chat_id, message_id):
    time.sleep(300)
    try:
        bot.delete_message(chat_id, message_id)
    except:
        pass

# =========================
# WEBHOOK
# =========================

@app.route("/")
def home():
    return "OK"

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK"

# =========================
# COMMANDS
# =========================

@bot.message_handler(commands=['start'])
def start_cmd(message):
    save_group(message.chat.id)
    bot.send_message(message.chat.id, "🌸 قائمة التسجيل 📝", reply_markup=menu())

@bot.message_handler(commands=['schedule'])
def schedule_cmd(message):
    bot.send_message(message.chat.id, SCHEDULE_TEXT)

@bot.message_handler(commands=['rules'])
def rules_cmd(message):
    bot.send_message(message.chat.id, RULES_TEXT)

@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.send_message(message.chat.id, HELP_TEXT)

# =========================
# MENU (التسجيل)
# =========================

def menu():
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ قرأت", callback_data="read"),
         InlineKeyboardButton("✍️ سجل اسمي", callback_data="register")],
        [InlineKeyboardButton("🎧 مستمعة", callback_data="listener"),
         InlineKeyboardButton("⛔️ معتذرة", callback_data="excused")],
        [InlineKeyboardButton("❌ حذف اسمي", callback_data="remove")]
    ])

# =========================
# CALLBACKS
# =========================

@bot.callback_query_handler(func=lambda call: True)
def handle(call):
    bot.answer_callback_query(call.id)

    if call.data == "register":
        bot.send_message(call.message.chat.id, "تم تسجيلك ✍️")

    elif call.data == "listener":
        bot.send_message(call.message.chat.id, "تم تسجيلك كمستمعة 🎧")

    elif call.data == "excused":
        bot.send_message(call.message.chat.id, "تم تسجيلك كمعتذرة ⛔️")

    elif call.data == "remove":
        bot.send_message(call.message.chat.id, "تم حذف اسمك ❌")

# =========================
# WELCOME MESSAGE (GROUP ONLY)
# =========================

@bot.message_handler(content_types=["new_chat_members"])
def welcome(message):
    for u in message.new_chat_members:
        msg = bot.send_message(
            message.chat.id,
            f"أهلاً بكِ {u.first_name}\n\n{WELCOME_MESSAGE}"
        )
        threading.Thread(target=auto_delete, args=(message.chat.id, msg.message_id)).start()

# =========================
# RUN
# =========================

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
