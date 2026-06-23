import os
import telebot
import threading
import time
import asyncio
import asyncpg
import logging
from flask import Flask, request
from telebot import types
from datetime import datetime
import schedule

# إعدادات البيئة
TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
DATABASE_URL = os.environ.get("DATABASE_URL")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# --- النصوص المعتمدة ---
WELCOME_MESSAGE = """
مرحبا مرحبا بوصية رسول الله...
قال رسول الله ﷺ: "سيأتيكُم أقوامٌ يطلبونَ العِلمَ، فإذا رأيتُموهم فقولوا لَهُم: مَرحبًا مَرحبًا بوصيَّةِ رسولِ اللَّهِ صلَّى اللَّهُ عليهِ وسلَّمَ، واقْنوهُم". قلتُ للحَكَمِ: ما اقْنوهُم؟ قالَ: علِّموهُم.

أهلاً بكِ في أكاديمية معارج الإتقان 🕊🌴🌴🌴
يرجى قراءة قوانين الأكاديمية المثبتة والالتزام بها.
"""

SCHEDULE_TEXT = """
" ✍جدول حلقات المقرأة♕
꧁꧁꧁꧁꧂꧂꧂꧂
💐 المعلمة : لطيفة تصحيح تلاوة 📝 المشرفة : دنيا ⏰ التوقيت : الأثنين 12مكة
💐 المعلمة : لطيفة المخارج 📝 المشرفة : دنيا ⏰ التوقيت : الثلاثاء 12مكة 
💐 المعلمة : لطيفة تأهيل المعلمات 📝 المشرفة : دنيا ⏰ التوقيت : الأربعاء 12مكة
💐 المعلمة : لطيفة ربع يس 📝 المشرفة : احلام وليلي ⏰ التوقيت : الخميس 12 مكة 
💐 المعلمة : منى الدسوقي أصول ورش 📝 المشرفة : لطيفة ⏰ التوقيت : الأثنين والاربعاء 5م مكة
💐 المعلمة : عالية محمد تصحيح تلاوة جزء عم 📝 المشرفة : ساجدة علي ⏰ التوقيت : 6:00 م مكة
💐 المعلمة : إيمان عجلان تصحيح جزء عم حفص 📝 المشرفة : ---- ⏰ التوقيت : السبت 10 ص مكة
💐 المعلمة : يسر أم عبد الرحمن تصحيح جزء تبارك 📝 المشرفة : متى يوسفي ⏰ التوقيت : 10 م مكة
💐 المعلمة : أميرة عزت شرح أحكام النون الساكنة 📝 المشرفة : دنيا ⏰ التوقيت : الاحد 3 ع مكة
💐 المعلمة : مريم ياسين 📝 المشرفة : --- ⏰ التوقيت : 3 م ليبيا
💐 المعلمة : عائشة عبدالسلام حفظ البقرة قالون 📝 المشرفة : ليلى القطروني ⏰ التوقيت : الثلاثاء 3 م 
💐 المعلمة : نهى السعيد حفظ ربع يس حفص 📝 المشرفة : ليلى القطروني ⏰ التوقيت : السبت 2 ظهرا مصر
💐 المعلمة : أم ساجدة 📝 المشرفة : ساجدة ⏰ التوقيت : 10 ص ليبيا 
💐 المعلمة : نسمه طه تصحيح تبارك وعم 📝 المشرفة : --- ⏰ التوقيت : الخميس 4 م مصر
💐 المعلمة : فاطمه فتحي حفظ تبارك وعم حفص 📝 المشرفة : --- ⏰ التوقيت : الثلاثاء 10 ص مكة ومصر 
💐 المعلمة : ميمونة تصحيح تلاوة 📝 المشرفة : زهراء اماني ⏰ التوقيت : الاحد 2 م مكة 
💐 المعلمة : زهراء 📝 المشرفة : اماني علي ⏰ التوقيت : السبت 5 م مصر 
💐 المعلمة : نسرين بركات 📝 المشرفة : ميمونة ⏰ التوقيت : السبت 3 م مصر 

القرآن في الدنيا نافع🍃 وفي القبر شافع🍃 وفي الجنة رافع🍃
اللهم اجعلنا من أهله وخاصته🤲🌹
꧁꧁꧁꧁꧂꧂꧂꧂"
"""

RULES_TEXT = """
بسم الله الرحمن الرحيم 
أكاديمية معارج الاتقان 🕊🌴🌴🌴
قوانين الأكاديمية:
1. الأكاديمية خاصة بالنساء فقط، يمنع منعاً باتاً انضمام الرجال.🚫
2. ليس هنالك شروط للإنضمام سوى الإنضباط.👩‍✈️
3. الرجاء كتابه الاسم بوضوح وعدم استخدام الرموز.❌
4. ممنوع نشر الروابط غير المتعلقة بالأكاديمية.🛑
5. ممنوع التواصل مع المعلمات في الخاص.✋
💐💐شاكرين حسن تعاونكن.
"""

HELP_TEXT = """
🌸 **قائمة أوامر مساعد أكاديمية معارج الإتقان** 🌸
📌 /rules : لعرض قوانين الأكاديمية.
📌 /schedule : لعرض جدول الحلقات.
📌 /help : لعرض هذه القائمة.
📌 /ban : لحظر عضوة (بالرد على رسالتها).
📌 /unban : لفك الحظر (بالرد على رسالتها).
"""

# --- منطق قاعدة البيانات ---
def run_async(coro): return asyncio.run(coro)

async def get_db(): return await asyncpg.connect(DATABASE_URL)

async def add_user_db(chat_id, user_id, name, status):
    conn = await get_db()
    await conn.execute("""INSERT INTO users (chat_id,user_id,name,status,read_status,created_at)
        VALUES ($1,$2,$3,$4,FALSE,$5) ON CONFLICT (chat_id,user_id) DO UPDATE SET status=$4, created_at=$5""", 
        chat_id, user_id, name, status, datetime.now())
    await conn.close()

async def build_list(chat_id):
    conn = await get_db()
    data = await conn.fetch("SELECT name,status,read_status FROM users WHERE chat_id=$1 ORDER BY created_at ASC", chat_id)
    row = await conn.fetchrow("SELECT locked FROM groups WHERE chat_id=$1", chat_id)
    locked = row['locked'] if row else False
    await conn.close()
    
    status_text = "🔒 التسجيل مغلق" if locked else "🔓 التسجيل مفتوح"
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def section(s):
        res = [f"{r['name']}{' ✅' if r['read_status'] else ''}" for r in data if r['status'] == s]
        return "\n".join(f"{i+1}- {x}" for i, x in enumerate(res)) if res else "لا يوجد"
    
    return (f"السلام عليكم ورحمة الله وبركاته\n📅 {date_str}\n\n"
            f"خادم القرآن الرقمي 💫\n{status_text}\n\n📋 قائمة التسجيل:\n\n"
            f"✍️ المسجلات:\n{section('register')}\n\n"
            f"⛔️ المعتذرات:\n{section('excused')}\n\n"
            f"🎧 المستمعات:\n{section('listener')}\n\n"
            f"🚫 المحظورات:\n{section('banned')}\n\n"
            "وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ۚ وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ")

# --- الهاندلرز ---
@bot.message_handler(commands=['start'])
def start(m):
    text = run_async(build_list(m.chat.id))
    bot.send_message(m.chat.id, text, reply_markup=get_menu())

@bot.message_handler(commands=['rules'])
def rules(m): bot.send_message(m.chat.id, RULES_TEXT)

@bot.message_handler(commands=['schedule'])
def schedule_cmd(m): bot.send_message(m.chat.id, SCHEDULE_TEXT)

@bot.message_handler(commands=['help'])
def help_cmd(m): bot.send_message(m.chat.id, HELP_TEXT, parse_mode="Markdown")

@bot.message_handler(commands=['ban'])
def ban(m):
    if m.reply_to_message:
        u = m.reply_to_message.from_user
        run_async(add_user_db(m.chat.id, u.id, u.full_name, "banned"))
        bot.reply_to(m, f"تم حظر {u.full_name}")

@bot.message_handler(commands=['unban'])
def unban(m):
    if m.reply_to_message:
        u = m.reply_to_message.from_user
        async def task():
            conn = await get_db()
            await conn.execute("DELETE FROM users WHERE chat_id=$1 AND user_id=$2", m.chat.id, u.id)
            await conn.close()
        run_async(task())
        bot.reply_to(m, f"تم فك الحظر عن {u.full_name}")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id, user_id, action = call.message.chat.id, call.from_user.id, call.data
    
    # تنفيذ الأوامر
    if action in ["register", "listener", "excused"]: 
        run_async(add_user_db(chat_id, user_id, call.from_user.full_name, action))
    elif action == "read":
        async def task():
            conn = await get_db()
            await conn.execute("UPDATE users SET read_status = NOT read_status WHERE chat_id=$1 AND user_id=$2", chat_id, user_id)
            await conn.close()
        run_async(task())
    elif action == "remove":
        async def task():
            conn = await get_db()
            await conn.execute("DELETE FROM users WHERE chat_id=$1 AND user_id=$2", chat_id, user_id)
            await conn.close()
        run_async(task())
    elif action == "reset":
        async def task():
            conn = await get_db()
            await conn.execute("DELETE FROM users WHERE chat_id=$1 AND status!='banned'", chat_id)
            await conn.close()
        run_async(task())
    elif action == "lock":
        async def task():
            conn = await get_db()
            await conn.execute("UPDATE groups SET locked = NOT locked WHERE chat_id=$1", chat_id)
            await conn.close()
        run_async(task())
        
    new_text = run_async(build_list(chat_id))
    try: bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=new_text, reply_markup=get_menu())
    except: pass

def get_menu():
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("✅ قرأت", callback_data="read"), types.InlineKeyboardButton("✍️ سجل اسمي", callback_data="register"))
    markup.row(types.InlineKeyboardButton("🎧 مستمعة", callback_data="listener"), types.InlineKeyboardButton("⛔️ معتذرة", callback_data="excused"))
    markup.row(types.InlineKeyboardButton("🔒 قفل/فتح", callback_data="lock"), types.InlineKeyboardButton("❌ حذف اسمي", callback_data="remove"))
    markup.row(types.InlineKeyboardButton("🧹 تصفير القائمة", callback_data="reset"))
    return markup

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return 'OK', 200

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL.rstrip('/')}/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

