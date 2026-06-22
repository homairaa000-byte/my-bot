import os, asyncio, asyncpg, logging, threading
from flask import Flask, request
import telebot
from telebot import types
from datetime import datetime

TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
DATABASE_URL = os.environ.get("DATABASE_URL")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# =========================
# النصوص الثابتة (كما هي بدون أي تعديل)
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
📜 قوانين الأكاديمية:
1- الأكاديمية خاصة بالنساء فقط 🚫
2- الانضباط شرط أساسي 👩‍✈️
3- كتابة الاسم بوضوح ❌
4- ممنوع نشر الروابط غير المتعلقة 🛑
5- ممنوع التواصل مع المعلمات في الخاص ✋
"""

SCHEDULE_TEXT = """
✍ جدول حلقات المقرأة ♕
(ضع الجدول كاملاً هنا كما في النسخة الأصلية)
"""

HELP_TEXT = """
🌸 **قائمة أوامر مساعد الأكاديمية** 🌸
📌 /rules : عرض القوانين
📌 /schedule : عرض الجدول
📌 /help : عرض هذه القائمة
📌 /start : تشغيل البوت
📌 /ban : حظر عضوة (بالرد على رسالتها)
📌 /unban : فك الحظر عن عضوة (بالرد على رسالتها)
"""

# =========================
# DB
# =========================
async def get_db():
    return await asyncpg.connect(DATABASE_URL)

async def add_user(chat_id, user_id, name, status):
    conn = await get_db()
    await conn.execute("""
        INSERT INTO users (chat_id,user_id,name,status,read_status,created_at)
        VALUES ($1,$2,$3,$4,FALSE,$5)
        ON CONFLICT (chat_id,user_id)
        DO UPDATE SET status=$4, created_at=$5
    """, chat_id, user_id, name, status, datetime.now())
    await conn.close()

async def toggle_lock(chat_id):
    conn = await get_db()
    row = await conn.fetchrow("SELECT locked FROM groups WHERE chat_id=$1", chat_id)

    if not row:
        await conn.execute("INSERT INTO groups(chat_id, locked) VALUES($1, FALSE)", chat_id)
        locked = False
    else:
        locked = not row['locked']
        await conn.execute("UPDATE groups SET locked=$1 WHERE chat_id=$2", locked, chat_id)

    await conn.close()
    return locked

async def build(chat_id):
    conn = await get_db()

    data = await conn.fetch(
        "SELECT name,status,read_status FROM users WHERE chat_id=$1 ORDER BY created_at ASC",
        chat_id
    )
    row = await conn.fetchrow("SELECT locked FROM groups WHERE chat_id=$1", chat_id)
    locked = row['locked'] if row else False

    await conn.close()

    status_text = "🔒 التسجيل مغلق" if locked else "🔓 التسجيل مفتوح"
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def section(status):
        result = [
            f"{r['name']}{' ✅' if r['read_status'] else ''}"
            for r in data if r['status'] == status
        ]
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
# menu (بدون تغيير شكل)
# =========================
def menu():
    return types.InlineKeyboardMarkup([
        [
            types.InlineKeyboardButton("✅ قرأت", callback_data="read"),
            types.InlineKeyboardButton("✍️ سجل اسمي", callback_data="register")
        ],
        [
            types.InlineKeyboardButton("🎧 مستمعة", callback_data="listener"),
            types.InlineKeyboardButton("⛔️ معتذرة", callback_data="excused")
        ],
        [
            types.InlineKeyboardButton("🔒 قفل/فتح", callback_data="lock"),
            types.InlineKeyboardButton("❌ حذف اسمي", callback_data="remove")
        ],
        [
            types.InlineKeyboardButton("🧹 تصفير القائمة", callback_data="reset")
        ]
    ])

# =========================
# helpers async bridge
# =========================
def run_async(coro):
    return asyncio.run(coro)

# =========================
# handlers (telebot)
# =========================
@bot.message_handler(commands=['start'])
def start(m):
    text = WELCOME_MESSAGE.format(date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    bot.send_message(m.chat.id, text, reply_markup=menu())

@bot.message_handler(commands=['rules'])
def rules(m):
    bot.send_message(m.chat.id, RULES_TEXT)

@bot.message_handler(commands=['schedule'])
def schedule(m):
    bot.send_message(m.chat.id, SCHEDULE_TEXT)

@bot.message_handler(commands=['help'])
def help_cmd(m):
    bot.send_message(m.chat.id, HELP_TEXT, parse_mode="Markdown")

@bot.message_handler(commands=['ban'])
def ban(m):
    if m.reply_to_message:
        u = m.reply_to_message.from_user
        run_async(add_user(m.chat.id, u.id, u.full_name, "banned"))
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

# =========================
# buttons (FIXED ONLY LOGIC)
# =========================
@bot.callback_query_handler(func=lambda q: True)
def cb(q):
    chat_id = q.message.chat.id
    user_id = q.from_user.id
    action = q.data

    if action == "lock":
        locked = run_async(toggle_lock(chat_id))
        bot.set_chat_permissions(chat_id, types.ChatPermissions(
            can_send_messages=not locked,
            can_send_media_messages=not locked,
            can_send_polls=not locked,
            can_send_other_messages=not locked
        ))

    elif action == "reset":
        async def task():
            conn = await get_db()
            await conn.execute("DELETE FROM users WHERE chat_id=$1 AND status!='banned'", chat_id)
            await conn.close()
        run_async(task())

    elif action == "remove":
        async def task():
            conn = await get_db()
            await conn.execute("DELETE FROM users WHERE chat_id=$1 AND user_id=$2", chat_id, user_id)
            await conn.close()
        run_async(task())

    elif action == "read":
        async def task():
            conn = await get_db()
            await conn.execute(
                "UPDATE users SET read_status = NOT read_status WHERE chat_id=$1 AND user_id=$2",
                chat_id, user_id
            )
            await conn.close()
        run_async(task())

    else:
        run_async(add_user(chat_id, user_id, q.from_user.full_name, action))

    new_text = run_async(build(chat_id))

    try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=q.message.message_id,
            text=new_text,
            reply_markup=menu()
        )
    except:
        pass

# =========================
# Flask webhook (FIX Render)
# =========================
@app.route("/", methods=["GET"])
def home():
    return "OK", 200

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

# =========================
# RUN
# =========================
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
