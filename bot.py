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

# --- دالة الحذف التلقائي ---
def safe_delete(chat_id, message_id):
    try: bot.delete_message(chat_id, message_id)
    except: pass

@app.route("/", methods=["GET"])
def index():
    return "البوت يعمل بنجاح!", 200

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
SCHEDULE_TEXT = """ ✍جدول حلقات المقرأة♕
꧁꧁꧁꧁꧂꧂꧂꧂
💐 المعلمة : لطيفة تصحيح تلاوة | المشرفة : دنيا | التوقيت : الأثنين 12مكة
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : لطيفة المخارج | المشرفة : دنيا | التوقيت : الثلاثاء 12مكة 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : لطيفة | المشرفة : دنيا | التوقيت : الأربعاء تأهيل المعلمات 12مكة
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : لطيفة ربع يس | المشرفة : احلام وليلي | التوقيت : الخميس 12 مكة 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : منى الدسوقي أصول ورش | المشرفة : لطيفة | التوقيت : الأثنين والاربعاء الخامسة مكة
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : عالية محمد جزء عم | المشرفة : ساجدة علي | التوقيت : 6:00 م مكة 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : إيمان عجلان جزء عم | المشرفة : ---- | التوقيت : السبت 10:00 ص مكة
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : يسر أم عبد الرحمن جزء تبارك | المشرفة : متى يوسفي | التوقيت : 10 مساءً مكة
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : أميرة عزت أحكام نون ساكنة | المشرفة : دنيا | التوقيت : الاحد 3 عصراً مكة 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : مريم ياسين | المشرفة : | التوقيت : الثالثة مساءً توقيت ليبيا
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : عائشة عبدالسلام حفظ البقرة | المشرفة : ليلي القطروني، ام سومه | التوقيت : الثلاثاء 3 مساءً
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : نهى السعيد حفظ ربع يس | المشرفة : ليلى القطرونى، عائشة عبد السلام | التوقيت : السبت 2 ظهراً مصر 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : أم ساجدة | المشرفة : ساجدة | التوقيت : العاشرة صباحاً توقيت ليبيا 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : نسمه طه تصحيح جزئى تبارك وعم | المشرفة : | التوقيت : الخميس 4 م توقيت مصر
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : فاطمه فتحي حفظ جزئى تبارك وعم | المشرفة : | التوقيت : الثلاثاء 10 ص مكة ومصر 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : ميمونة تصحيح تلاوة | المشرفة : زهراء اماني | التوقيت : الاحد 2 مكة 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : زهراء | المشرفة : اماني علي | التوقيت : السبت 5 بتوقيت مصر 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : نسرين بركات | المشرفة : ميمونة | التوقيت : السبت 3 مساءً بتوقيت مصر 
❀❀❀❀❀❀❀❀❀❀❀

القرآن في الدنيا نافع🍃، وفي القبر شافع🍃، وفي الجنة رافع🍃
اللهم اجعلنا من أهله وخاصته🤲🌹
꧁꧁꧁꧁꧂꧂꧂꧂"""

RULES_TEXT = """بسم الله الرحمن الرحيم 
أكاديمية معارج الاتقان 🕊🌴🌴🌴
قوانين الأكاديمية:
1. الأكاديمية خاصه بالنساء فقط، يمنع انضمام الرجال.🚫
2. لا شروط للإنضمام سوى الإنضباط.👩‍✈️
3. كتابة الاسم بوضوح وبدون رموز.❌
4. مجموعات الحفظ: التواصل مع مشرفات المجموعات المذكورات في الجدول.
5. ممنوع نشر الروابط غير المتعلقة بالأكاديمية.🛑
6. ممنوع التواصل مع المعلمات في الخاص، أي استفسار يرسل هنا أو للمشرفات.✋
💐شاكرين حسن تعاونكن."""

# --- الدوال الأساسية ---
def build_list(chat_id):
    users = db_fetch("SELECT name, status, read_status FROM users WHERE chat_id=?", (chat_id,))
    group = db_fetch("SELECT locked FROM groups WHERE chat_id=?", (chat_id,))
    locked = group[0][0] if group else False
    status_text = "🔒 التسجيل مغلق" if locked else "🔓 التسجيل مفتوح"
    def section(s):
        res = [f"{r[0]}{' ✅' if r[2] else ''}" for r in users if r[1] == s]
        return "\n".join(f"{i+1}- {x}" for i, x in enumerate(res)) if res else "لا يوجد"
    return (f"السلام عليكم ورحمة الله وبركاته\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"خادم القرآن الرقمي 💫\n{status_text}\n\n📋 قائمة التسجيل:\n\n"
            f"✍️ المسجلات:\n{section('register')}\n\n⛔️ المعتذرات:\n{section('excused')}\n\n"
            f"🎧 المستمعات:\n{section('listener')}\n\n🚫 المحظورات:\n{section('banned')}\n\n"
            "وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ۚ وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ")

def get_menu():
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("✅ قرأت", callback_data="read"), types.InlineKeyboardButton("✍️ سجل اسمي", callback_data="register"))
    markup.row(types.InlineKeyboardButton("🎧 مستمعة", callback_data="listener"), types.InlineKeyboardButton("⛔️ معتذرة", callback_data="excused"))
    markup.row(types.InlineKeyboardButton("🔒 قفل/فتح", callback_data="lock"), types.InlineKeyboardButton("❌ حذف اسمي", callback_data="remove"))
    markup.row(types.InlineKeyboardButton("🧹 تصفير القائمة", callback_data="reset"))
    return markup

def is_admin(chat_id, user_id):
    try: return bot.get_chat_member(chat_id, user_id).status in ['administrator', 'creator']
    except: return False

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    bot.answer_callback_query(call.id)
    chat_id, user_id, action = call.message.chat.id, call.from_user.id, call.data
    if action in ["lock", "reset"] and not is_admin(chat_id, user_id):
        return
    
    if action == "reset":
        db_execute("DELETE FROM users WHERE chat_id=?", (chat_id,))
    elif action == "lock":
        db_execute("UPDATE groups SET locked = NOT locked WHERE chat_id=?", (chat_id,))
    
    elif action in ["register", "listener", "excused"]:
        locked = db_fetch("SELECT locked FROM groups WHERE chat_id=?", (chat_id,))
        if locked and locked[0][0]: return
        db_execute("DELETE FROM users WHERE chat_id=? AND user_id=? AND status != 'banned'", (chat_id, user_id))
        db_execute("INSERT INTO users (chat_id, user_id, name, status, read_status) VALUES (?,?,?,?,?)", (chat_id, user_id, call.from_user.full_name, action, False))
    elif action == "read":
        db_execute("UPDATE users SET read_status = NOT read_status WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    elif action == "remove":
        db_execute("DELETE FROM users WHERE chat_id=? AND user_id=? AND status != 'banned'", (chat_id, user_id))
        
    try: bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=build_list(chat_id), reply_markup=get_menu())
    except: pass

@bot.message_handler(commands=['start'])
def start(m):
    if not is_admin(m.chat.id, m.from_user.id): return
    safe_delete(m.chat.id, m.message_id)
    db_execute("INSERT OR IGNORE INTO groups (chat_id, locked) VALUES (?, ?)", (m.chat.id, False))
    bot.send_message(m.chat.id, build_list(m.chat.id), reply_markup=get_menu())

# --- دالة الترحيب ---
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(m):
    for member in m.new_chat_members:
        welcome_text = f"أهلاً بكِ يا {member.full_name} في أكاديمية معارج الاتقان! 🕊\nيرجى قراءة القوانين في المثبتة."
        sent_msg = bot.send_message(m.chat.id, welcome_text)
        threading.Timer(300, safe_delete, args=[m.chat.id, sent_msg.message_id]).start()

# --- الأوامر المضافة ---
@bot.message_handler(commands=['rules'])
def rules(m):
    safe_delete(m.chat.id, m.message_id)
    bot.send_message(m.chat.id, RULES_TEXT)

@bot.message_handler(commands=['schedule'])
def schedule(m):
    safe_delete(m.chat.id, m.message_id)
    bot.send_message(m.chat.id, SCHEDULE_TEXT)

@bot.message_handler(commands=['ban'])
def ban_user(m):
    if not is_admin(m.chat.id, m.from_user.id): return
    safe_delete(m.chat.id, m.message_id)
    if m.reply_to_message:
        target = m.reply_to_message.from_user
        db_execute("DELETE FROM users WHERE chat_id=? AND user_id=?", (m.chat.id, target.id))
        db_execute("INSERT INTO users (chat_id, user_id, name, status, read_status) VALUES (?,?,?,?,?)", (m.chat.id, target.id, target.full_name, 'banned', False))
        bot.send_message(m.chat.id, f"✅ تم حظر: {target.full_name}")

@bot.message_handler(commands=['unban'])
def unban_user(m):
    if not is_admin(m.chat.id, m.from_user.id): return
    safe_delete(m.chat.id, m.message_id)
    if m.reply_to_message:
        target = m.reply_to_message.from_user
        db_execute("DELETE FROM users WHERE chat_id=? AND user_id=? AND status='banned'", (m.chat.id, target.id))
        bot.send_message(m.chat.id, f"✅ تم فك الحظر عن: {target.full_name}")

@bot.message_handler(commands=['backup'])
def backup_db(m):
    if m.from_user.id != 1942624918: return
    try:
        with open('data.db', 'rb') as db_file:
            bot.send_document(m.chat.id, db_file, caption="نسخة احتياطية لقاعدة البيانات")
    except Exception as e:
        bot.send_message(m.chat.id, f"خطأ: {e}")

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return 'OK', 200

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL.rstrip('/')}/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

