import os
import telebot
import sqlite3
import threading
from flask import Flask, request
from telebot import types
from datetime import datetime

TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- تهيئة قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('data.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (chat_id INTEGER, user_id INTEGER, name TEXT, status TEXT, read_status BOOLEAN)''')
    c.execute('''CREATE TABLE IF NOT EXISTS groups (chat_id INTEGER PRIMARY KEY, locked BOOLEAN)''')
    conn.commit()
    conn.close()

init_db()

def db_execute(query, params=()):
    conn = sqlite3.connect('data.db', check_same_thread=False)
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    conn.close()

def db_fetch(query, params=()):
    conn = sqlite3.connect('data.db', check_same_thread=False)
    c = conn.cursor()
    c.execute(query, params)
    data = c.fetchall()
    conn.close()
    return data

# --- النصوص المعتمدة ---
WELCOME_MESSAGE = """
مرحبا مرحبا بوصية رسول الله...
قال رسول الله ﷺ: "سيأتيكُم أقوامٌ يطلبونَ العِلمَ، فإذا رأيتُموهم فقولوا لَهُم: مَرحبًا مَرحبًا بوصيَّةِ رسولِ اللَّهِ صلَّى اللَّهُ عليهِ وسلَّمَ، واقْنوهُم". قلتُ للحَكَمِ: ما اقْنوهُم؟ قالَ: علِّموهُم.

أهلاً بكِ في أكاديمية معارج الإتقان 🕊🌴🌴🌴
يرجى قراءة قوانين الأكاديمية المثبتة والالتزام بها.
"""

SCHEDULE_TEXT = """
 ✍جدول حلقات المقرأة♕
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
📆   اليوم:  السبت 
⏰ التوقيت : 5 بتوقيت مصر 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : نسرين بركات 
📝 المشرفة : ميمونة 
📆   اليوم:  السبت 
⏰ التوقيت : 3 مساء بتوقيت مصر 
❀❀❀❀❀❀❀❀❀❀❀
القرآن في الدنيا نافع🍃
‏وفي القبر شافع🍃
‏وفي الجنة رافع🍃
‏اللهم اجعلنا من أهله وخاصته🤲🌹
꧁꧁꧁꧁꧂꧂꧂꧂
"""

RULES_TEXT = """
بسم الله الرحمن الرحيم 
أكاديمية معارج الاتقان 🕊🌴🌴🌴
قوانين الأكاديمية:
🌴🌴الأكاديمية تعنى بتقديم كل ما يتعلق بالتجويد والقران من حصص تجويد وتصحيح تلاوه وقراءات وغيرها من المجالات. 
1. الأكاديمية خاصه بالنساء فقط، يمنع منعاً باتاً انضمام الرجال.🚫🚫🚫
2. ليس هنالك شروط للإنضمام للأكاديمية سوى الإنضباط.👩‍✈️👩‍✈️
3. الرجاء كتابه الاسم بوضوح وعدم استخدام الرموز (والاولاد بدون كلمة أم) حتى لا يتم ازالتك.❌❌
4. مجموعات الحفظ بروايه قالون: ربع يس تحت إشراف المعلمة أم ساجدة، و ربع البقرة تحت اشراف المعلمة مريم، و جزء عم و تبارك تحت إشراف المعلمه يسر ورغي @Yosrwerghi، كل من تريد الإنضمام الى مجموعات الحفظ برواية قانون تتواصل مع مسؤولات المجموعات. 
5. مجموعات الحفظ برواية حفص: ربع يس تحت إشراف المعلمة نهى سعيد، و ليلى القطروني، جزئي تبارك و عم تحت اشراف المعلمة فاطمة فتحي، و ربع البقرة تحت إشراف المعلمة زهراء @Zahraamohamed_mahsoup18 والمعلمة أماني amani وميمونة @Aminaoon.
6. ليس لدينا مجموعات حفظ برواية ورش بعد.
🌼🌺 كل من تريد الإنضمام إلى المجموعات او السؤال عن اي شيء يتعلق بها التواصل مع مشرفات المجموعات.
7. ممنوع نشر الروابط غير المتعلقة بالأكاديمية . 🛑🛑🛑
8. ممنوع التواصل مع المعلمات في الخاص، أي استفسار يرسل هنا على المقراة أو لمشرفات المجموعات.✋✋
💐💐شاكرين حسن تعاونكن لننهض جميعا بصرح تعليمي شامخ.
"""

# --- القائمة المحدثة بالترتيب المطلوب ---
def build_list(chat_id):
    users = db_fetch("SELECT name, status, read_status FROM users WHERE chat_id=?", (chat_id,))
    group = db_fetch("SELECT locked FROM groups WHERE chat_id=?", (chat_id,))
    locked = group[0][0] if group else False
    
    status_text = "🔒 التسجيل مغلق" if locked else "🔓 التسجيل مفتوح"
    
    def section(s):
        res = [f"{r[0]}{' ✅' if r[2] else ''}" for r in users if r[1] == s]
        return "\n".join(f"{i+1}- {x}" for i, x in enumerate(res)) if res else "لا يوجد"
    
    # الترتيب: السلام، ثم العنوان، ثم القائمة، ثم الآية
    return (f"السلام عليكم ورحمة الله وبركاته\n\n"
            f"خادم القرآن الرقمي 💫\n{status_text}\n\n📋 قائمة التسجيل:\n\n"
            f"✍️ المسجلات:\n{section('register')}\n\n"
            f"⛔️ المعتذرات:\n{section('excused')}\n\n"
            f"🎧 المستمعات:\n{section('listener')}\n\n"
            f"🚫 المحظورات:\n{section('banned')}\n\n"
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ۚ وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ")

def get_menu():
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("✅ قرأت", callback_data="read"), types.InlineKeyboardButton("✍️ سجل اسمي", callback_data="register"))
    markup.row(types.InlineKeyboardButton("🎧 مستمعة", callback_data="listener"), types.InlineKeyboardButton("⛔️ معتذرة", callback_data="excused"))
    markup.row(types.InlineKeyboardButton("🔒 قفل/فتح", callback_data="lock"), types.InlineKeyboardButton("❌ حذف اسمي", callback_data="remove"))
    markup.row(types.InlineKeyboardButton("🧹 تصفير القائمة", callback_data="reset"))
    return markup

# --- الدوال والأزرار ---
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    chat_id, user_id, action = call.message.chat.id, call.from_user.id, call.data
    if action in ["register", "listener", "excused"]:
        db_execute("DELETE FROM users WHERE chat_id=? AND user_id=? AND status != 'banned'", (chat_id, user_id))
        db_execute("INSERT INTO users (chat_id, user_id, name, status, read_status) VALUES (?,?,?,?,?)", (chat_id, user_id, call.from_user.full_name, action, False))
    elif action == "read":
        db_execute("UPDATE users SET read_status = NOT read_status WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    elif action == "remove":
        db_execute("DELETE FROM users WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    elif action == "reset":
        db_execute("DELETE FROM users WHERE chat_id=? AND status != 'banned'", (chat_id,))
    elif action == "lock":
        db_execute("UPDATE groups SET locked = NOT locked WHERE chat_id=?", (chat_id,))
    
    try: bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=build_list(chat_id), reply_markup=get_menu())
    except: pass

@bot.message_handler(commands=['start'])
def start(m):
    db_execute("INSERT OR IGNORE INTO groups (chat_id, locked) VALUES (?, ?)", (m.chat.id, False))
    bot.send_message(m.chat.id, WELCOME_MESSAGE)
    bot.send_message(m.chat.id, build_list(m.chat.id), reply_markup=get_menu())

@bot.message_handler(commands=['rules'])
def rules(m): bot.send_message(m.chat.id, RULES_TEXT)

@bot.message_handler(commands=['schedule'])
def schedule(m): bot.send_message(m.chat.id, SCHEDULE_TEXT)

@bot.message_handler(func=lambda m: True)
def filter_msg(m):
    try:
        if bot.get_chat_member(m.chat.id, m.from_user.id).status not in ["administrator", "creator"]:
            if any(x in (m.text or m.caption or "").lower() for x in ["http", "t.me", "wa.me"]):
                bot.delete_message(m.chat.id, m.message_id)
    except: pass

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return 'OK', 200

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL.rstrip('/')}/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

