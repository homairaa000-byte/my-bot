import os
import telebot
import sqlite3
import threading
import re
from flask import Flask, request
from telebot import types
from telebot.util import content_type_service
from datetime import datetime

TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)


# --- دالة الحذف التلقائي الآمنة ---
def safe_delete(chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except:
        pass


@app.route("/", methods=["GET"])
def index():
    return "البوت يعمل بنجاح!", 200


# --- تهيئة قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('data.db', check_same_thread=False)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER,
            user_id INTEGER,
            name TEXT,
            status TEXT,
            read_status BOOLEAN
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            chat_id INTEGER PRIMARY KEY,
            locked BOOLEAN
        )
    ''')

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


# --- النصوص المعتمدة (قوانين الأكاديمية والشروط الجديدة) ---
RULES_TEXT = """بسم الله الرحمن الرحيم 
أكاديمية معارج الاتقان 🕊🌴🌴🌴
قوانين الأكاديمية:
1. الأكاديمية خاصه بالنساء فقط، يمنع انضمام الرجال.🚫
2. لا شروط للإنضمام سوى الإنضباط.👩‍✈️
3. كتابة الاسم بوضوح وبدون رموز.❌
4. مجموعات الحفظ: التواصل مع مشرفات المجموعات المذكورات في الجدول.
5. ممنوع نشر الروابط غير المتعلقة بالأكاديمية.🛑
6. ممنوع التواصل مع المعلمات في الخاص، أي استفسار يرسل هنا أو للمشرفات.✋
💐شاكرين حسن تعاونكن.

✅شروط وضوابط حلقات المقرأة❌

❤️التحلي بأخلاق طالب العلم.
🌼التأدب بآداب حملة القرآن الكريم.
🌾احترام الوقت والميعاد والمعلمة.
✅أخذ الأدوار قبل ساعة أو نصف ساعة من بداية الحلقة.
📌الالتزام بالحضور المنتظم، وعدم الانقطاع إلا لعذر.
📌إبلاغ المعلمة مسبقًا عند تعذر الحضور.
📒📕الاستعداد للحلقة قبل بدايتها، وإحضار المصحف والأدوات اللازمة.
❄️الإنصات للمعلمة أثناء التصحيح وعدم مقاطعتها.
☎️📱عدم الانشغال بالهاتف أو المحادثات الجانبية أثناء الحلقة.
🔴عدم إرسال الرسائل أو التسجيلات في مجموعة الحلقة إلا فيما يخص المقرأة.
🔊المحافظة على هدوء الحلقة وعدم التشويش على الأخوات.
الاستئذان قبل الحديث أو مغادرة الحلقة.
🩷تقبّل التصحيح والملاحظات بصدر رحب، والعمل على تدارك الأخطاء.
♦️المحافظة على خصوصية ما يدور داخل الحلقة وعدم نقل ما يخص الطالبات.
💛التعاون مع الزميلات فيما يعود بالنفع على الحلقة، دون الانشغال عن الهدف الأساسي.
⁉️المبادرة بالسؤال عند عدم فهم حكم أو تصحيح، وعدم ترك الخطأ دون معرفة الصواب.
🔴المحافظة على سرية بيانات الطالبات وأرقام التواصل وعدم مشاركتها دون إذن.
🛎️الالتزام بالهدوء انتظار الدور، وعدم استعجال المعلمة أو الطالبة التي قبلها.
🤍🤍أن يكون حضور الحلقة بقصد الانتفاع بالقرآن وتعلمه وإتقانه، لا لمجرد إتمام الحضور."""


# --- الدوال الأساسية وقوائم الأزرار ---
def build_list(chat_id):
    users = db_fetch(
        "SELECT name, status, read_status FROM users WHERE chat_id=?",
        (chat_id,)
    )

    group = db_fetch(
        "SELECT locked FROM groups WHERE chat_id=?",
        (chat_id,)
    )

    locked = group[0][0] if group else False
    status_text = "🔒 التسجيل مغلق" if locked else "🔓 التسجيل مفتوح"

    def section(s):
        res = [
            f"{r[0]}{' ✅' if r[2] else ''}"
            for r in users
            if r[1] == s
        ]

        return (
            "\n".join(f"{i+1}- {x}" for i, x in enumerate(res))
            if res else "لا يوجد"
        )

    return (
        f"السلام عليكم ورحمة الله وبركاته\n"
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"خادم القرآن الرقمي 💫\n"
        f"{status_text}\n\n"
        f"📋 قائمة التسجيل:\n\n"
        f"✍️ المسجلات:\n{section('register')}\n\n"
        f"⛔️ المعتذرات:\n{section('excused')}\n\n"
        f"🎧 المستمعات:\n{section('listener')}\n\n"
        f"🚫 المحظورات:\n{section('banned')}\n\n"
        "وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ۚ وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ"
    )


def get_menu():
    markup = types.InlineKeyboardMarkup()

    markup.row(
        types.InlineKeyboardButton(
            "✅ قرأت",
            callback_data="read"
        ),
        types.InlineKeyboardButton(
            "✍️ سجل اسمي",
            callback_data="register"
        )
    )

    markup.row(
        types.InlineKeyboardButton(
            "🎧 مستمعة",
            callback_data="listener"
        ),
        types.InlineKeyboardButton(
            "⛔️ معتذرة",
            callback_data="excused"
        )
    )

    markup.row(
        types.InlineKeyboardButton(
            "🔒 قفل/فتح",
            callback_data="lock"
        ),
        types.InlineKeyboardButton(
            "❌ حذف اسمي",
            callback_data="remove"
        )
    )

    markup.row(
        types.InlineKeyboardButton(
            "🧹 تصفير القائمة",
            callback_data="reset"
        )
    )

    return markup


def is_admin(chat_id, user_id):
    try:
        return bot.get_chat_member(
            chat_id,
            user_id
        ).status in ['administrator', 'creator']
    except:
        return False


# --- التعامل مع أزرار القائمة ---
@bot.callback_query_handler(func=lambda call: True)
def callback(call):

    bot.answer_callback_query(call.id)

    chat_id = call.message.chat.id
    user_id = call.from_user.id
    action = call.data

    # القفل والتصفير للمشرفين فقط
    if action in ["lock", "reset"] and not is_admin(chat_id, user_id):
        return

    # --- تصفير القائمة ---
    if action == "reset":
        db_execute(
            "DELETE FROM users WHERE chat_id=?",
            (chat_id,)
        )

    # --- قفل / فتح التسجيل ---
    elif action == "lock":
        db_execute(
            "UPDATE groups SET locked = NOT locked WHERE chat_id=?",
            (chat_id,)
        )

    # --- تسجيل / مستمعة / معتذرة ---
    elif action in ["register", "listener", "excused"]:

        locked = db_fetch(
            "SELECT locked FROM groups WHERE chat_id=?",
            (chat_id,)
        )

        if locked and locked[0][0]:
            return

        db_execute(
            "DELETE FROM users "
            "WHERE chat_id=? AND user_id=? AND status != 'banned'",
            (chat_id, user_id)
        )

        db_execute(
            "INSERT INTO users "
            "(chat_id, user_id, name, status, read_status) "
            "VALUES (?,?,?,?,?)",
            (
                chat_id,
                user_id,
                call.from_user.full_name,
                action,
                False
            )
        )

    # --- قرأت ---
    elif action == "read":
        db_execute(
            "UPDATE users "
            "SET read_status = NOT read_status "
            "WHERE chat_id=? AND user_id=?",
            (chat_id, user_id)
        )

    # --- حذف الاسم ---
    elif action == "remove":
        db_execute(
            "DELETE FROM users "
            "WHERE chat_id=? AND user_id=? AND status != 'banned'",
            (chat_id, user_id)
        )

    # تحديث القائمة
    try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=build_list(chat_id),
            reply_markup=get_menu()
        )
    except:
        pass


# --- أمر البداية ---
@bot.message_handler(commands=['start'])
def start(m):

    if not is_admin(m.chat.id, m.from_user.id):
        return

    safe_delete(
        m.chat.id,
        m.message_id
    )

    db_execute(
        "INSERT OR IGNORE INTO groups (chat_id, locked) VALUES (?, ?)",
        (m.chat.id, False)
    )

    bot.send_message(
        m.chat.id,
        build_list(m.chat.id),
        reply_markup=get_menu()
    )


# =========================================================
# 1. حذف إشعارات الانضمام والمغادرة
#    + إرسال الترحيب وحذفه بعد 5 دقائق
# =========================================================

@bot.message_handler(
    content_types=[
        'new_chat_members',
        'left_chat_member'
    ]
)
def welcome_new_member(m):

    # حذف رسالة الانضمام / المغادرة الخدمية فوراً
    safe_delete(
        m.chat.id,
        m.message_id
    )

    bot_id = bot.get_me().id

    # إذا كان هناك أعضاء جدد
    if m.new_chat_members:

        for member in m.new_chat_members:

            # تجاهل البوتات والبوت نفسه
            if member.id == bot_id or member.is_bot:
                continue

            user_mention = (
                f"[{member.first_name}]"
                f"(tg://user?id={member.id})"
            )

            welcome_text = (
                f"مرحباً مرحباً بوصية رسول الله ﷺ...\n"
                f"قال رسول الله ﷺ: "
                f"\"سيأتيكُم أقوامٌ يطلبونَ العلمَ، فإذا رأيتُموهم "
                f"فقولوا لَهم: مَرحبًا مَرحبًا بوصيَّةِ رسولِ اللَّهِ "
                f"صلَّى اللَّهُ عليْهِ وسلَّمَ، واقْنوهُم. "
                f"قلتُ لِلحَكمِ: ما اقْنوهُم؟ قالَ: علِّموهم.\"\n\n"
                f"أهلاً بكِ يا {user_mention} في أكاديمية معارج الاتقان! 🕊\n"
                f"أكاديميتنا ( للنساء فقط )\n"
                f"وحلقاتها كلها مجانا لوجه الله\n"
                f"نسأل الله التوفيق والسداد والإخلاص 🕊"
            )

            sent_msg = bot.send_message(
                m.chat.id,
                welcome_text,
                parse_mode="Markdown"
            )

            # حذف رسالة الترحيب بعد 5 دقائق
            threading.Timer(
                300,
                safe_delete,
                args=[
                    m.chat.id,
                    sent_msg.message_id
                ]
            ).start()


# =========================================================
# 2. حذف جميع رسائل النظام التي تدعمها المكتبة
# =========================================================

SYSTEM_MESSAGE_TYPES = [
    message_type
    for message_type in content_type_service
    if message_type not in [
        'new_chat_members',
        'left_chat_member'
    ]
]


@bot.message_handler(
    content_types=SYSTEM_MESSAGE_TYPES
)
def clean_system_messages(m):

    # حذف رسالة النظام فوراً
    safe_delete(
        m.chat.id,
        m.message_id
    )


# =========================================================
# 3. الأوامر الأساسية والإدارية
# =========================================================

@bot.message_handler(commands=['rules'])
def rules(m):

    safe_delete(
        m.chat.id,
        m.message_id
    )

    bot.send_message(
        m.chat.id,
        RULES_TEXT
    )


# --- الحظر داخل قائمة البوت فقط ---
@bot.message_handler(commands=['ban'])
def ban_user(m):

    if not is_admin(
        m.chat.id,
        m.from_user.id
    ):
        return

    safe_delete(
        m.chat.id,
        m.message_id
    )

    if m.reply_to_message:

        target = m.reply_to_message.from_user

        db_execute(
            "DELETE FROM users WHERE chat_id=? AND user_id=?",
            (m.chat.id, target.id)
        )

        db_execute(
            "INSERT INTO users "
            "(chat_id, user_id, name, status, read_status) "
            "VALUES (?,?,?,?,?)",
            (
                m.chat.id,
                target.id,
                target.full_name,
                'banned',
                False
            )
        )

        bot.send_message(
            m.chat.id,
            f"✅ تم حظر: {target.full_name}"
        )


# --- فك الحظر من قائمة البوت فقط ---
@bot.message_handler(commands=['unban'])
def unban_user(m):

    if not is_admin(
        m.chat.id,
        m.from_user.id
    ):
        return

    safe_delete(
        m.chat.id,
        m.message_id
    )

    if m.reply_to_message:

        target = m.reply_to_message.from_user

        db_execute(
            "DELETE FROM users "
            "WHERE chat_id=? AND user_id=? AND status='banned'",
            (m.chat.id, target.id)
        )

        bot.send_message(
            m.chat.id,
            f"✅ تم فك الحظر عن: {target.full_name}"
        )


# --- النسخة الاحتياطية ---
@bot.message_handler(commands=['backup'])
def backup_db(m):

    if m.from_user.id != 1942624918:
        return

    try:

        with open('data.db', 'rb') as db_file:

            bot.send_document(
                m.chat.id,
                db_file,
                caption="نسخة احتياطية لقاعدة البيانات"
            )

    except Exception as e:

        bot.send_message(
            m.chat.id,
            f"خطأ: {e}"
        )


# =========================================================
# 4. نظام الحماية
# =========================================================

@bot.message_handler(
    func=lambda m: True,
    content_types=[
        'text',
        'photo',
        'video',
        'document',
        'audio',
        'voice',
        'sticker'
    ]
)
def security_filter(m):

    # استثناء المشرفين والمالك تماماً
    if is_admin(
        m.chat.id,
        m.from_user.id
    ):
        return

    text_check = (
        m.text or
        m.caption or
        ""
    )

    # التقاط وحذف الرسائل الخدمية النصية
    if (
        "انضمام" in text_check or
        "رابط دعوة" in text_check or
        "بإضافة" in text_check or
        "أضاف" in text_check
    ):

        safe_delete(
            m.chat.id,
            m.message_id
        )

        return

    # --- فحص الروابط ---
    has_url = False

    if m.entities:

        for entity in m.entities:

            if entity.type in [
                'url',
                'text_link',
                'mention'
            ]:

                has_url = True

    # --- فحص أرقام الهاتف ---
    has_phone = bool(
        re.search(
            r'\+?\d[\d\-\s]{7,}\d',
            text_check
        )
    )

    # --- فحص الرسائل المعاد توجيهها ---
    is_forwarded = (
        m.forward_date is not None
    )

    # --- حذف المخالفة وإرسال التنبيه ---
    if has_url or has_phone or is_forwarded:

        safe_delete(
            m.chat.id,
            m.message_id
        )

        user_mention = (
            f"[{m.from_user.first_name}]"
            f"(tg://user?id={m.from_user.id})"
        )

        warning_text = (
            f"⛔️ تنبيه :\n"
            f"عذرا {user_mention} "
            f"إرسال روابط من دون إذن المشرفين "
            f"يعرضك للحذف أو الحظر"
        )

        warning_msg = bot.send_message(
            m.chat.id,
            warning_text,
            parse_mode="Markdown"
        )

        # حذف التحذير بعد 5 دقائق
        threading.Timer(
            300,
            safe_delete,
            args=[
                m.chat.id,
                warning_msg.message_id
            ]
        ).start()

        return


# =========================================================
# 5. Webhook المحدث
# =========================================================

@app.route(
    f"/{TOKEN}",
    methods=["POST"]
)
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return 'Forbidden', 403


# =========================================================
# 6. تشغيل البوت على Render
# =========================================================

if __name__ == "__main__":

    # الرابط الصحيح والمحدث لخدمتك الحالية على Render
    WEBHOOK_URL = "https://my-bot-nquv.onrender.com"

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    # إزالة الويب هوك القديم بشكل آمن
    bot.remove_webhook()

    # تعيين الويب هوك الجديد مع تفريغ التحديثات المعلقة داخل set_webhook
    bot.set_webhook(
        url=f"{WEBHOOK_URL.rstrip('/')}/{TOKEN}",
        drop_pending_updates=True,
        allowed_updates=[
            "message",
            "edited_message",
            "callback_query",
            "my_chat_member",
            "chat_member"
        ]
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
