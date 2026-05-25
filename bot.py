import os
import datetime
import pytz

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ===== التوكن =====
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise Exception("BOT_TOKEN missing")

# ===== البيانات =====
registered = {}
readers = set()
listeners = set()
excused = set()
blocked = set()

registration_open = True

# ===== الوقت =====
def now():
    tz = pytz.timezone("Asia/Riyadh")
    return datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M")

# ===== تنسيق المسجلات =====
def format_registered():
    if not registered:
        return "لا يوجد"

    text = ""

    for uid, name in registered.items():

        mark = ""
        if name in readers:
            mark = " ✅️"

        text += "• " + name + mark + "\n"

    return text

# ===== بناء القائمة =====
def build_text():

    status = "🔓 التسجيل مفتوح"

    if not registration_open:
        status = "🔒 التسجيل مغلق"

    listeners_text = "\n".join(listeners) if listeners else "لا يوجد"
    excused_text = "\n".join(excused) if excused else "لا يوجد"

    return (
        "السلام عليكم ورحمة الله وبركاته 🌿\n\n"
        "خادم القرآن الرقمي 🤍\n"
        "📅 " + now() + "\n\n"
        + status + "\n\n"

        "📌 قائمة تسجيل الأدوار\n\n"

        "✍️ المسجلات:\n"
        + format_registered() + "\n\n"

        "🎧 المستمعات:\n"
        + listeners_text + "\n\n"

        "⛔️ المعتذرات:\n"
        + excused_text + "\n\n"

        "﴿ وَالَّذِينَ جَاهَدُوا فِينَا "
        "لَنَهْدِيَنَّهُمْ سُبُلَنَا ۚ "
        "وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ ﴾"
    )

# ===== الأزرار =====
def menu():

    keyboard = [

        [
            InlineKeyboardButton(
                "✍️ سجل إسمي",
                callback_data="reg"
            ),

            InlineKeyboardButton(
                "📖 قرأت",
                callback_data="read"
            )
        ],

        [
            InlineKeyboardButton(
                "🎧 مستمعة",
                callback_data="listen"
            ),

            InlineKeyboardButton(
                "⛔ معتذرة",
                callback_data="excused"
            )
        ],

        [
            InlineKeyboardButton(
                "🔒 قفل / فتح",
                callback_data="toggle"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)

# ===== start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    welcome = (
        "🌿 أهلاً بك في خادم القرآن الرقمي 🤍\n\n"
        "• تسجيل الأدوار\n"
        "• تنظيم القراءة\n"
        "• متابعة المستمعات والمعتذرات\n\n"
        "🤍 اللهم اجعل أعمالنا خالصة لوجهك الكريم"
    )

    await update.message.reply_text(
        welcome
    )

    await update.message.reply_text(
        build_text(),
        reply_markup=menu()
    )

# ===== الأزرار =====
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global registration_open

    q = update.callback_query

    await q.answer()

    user = q.from_user

    uid = user.id
    name = user.first_name

    # 🚫 المحظورات
    if uid in blocked:

        await q.answer(
            "🚫 أنتِ محظورة",
            show_alert=True
        )

        return

    data = q.data

    # 🔒 إذا التسجيل مغلق
    if (
        not registration_open
        and data in ["reg", "read", "listen", "excused"]
    ):

        await q.answer(
            "🔒 التسجيل مغلق حالياً",
            show_alert=True
        )

        return

    # ===== العمليات =====

    if data == "reg":

        registered[uid] = name

    elif data == "read":

        if uid in registered:
            readers.add(name)

    elif data == "listen":

        listeners.add(name)

        registered.pop(uid, None)

        readers.discard(name)

        excused.discard(name)

    elif data == "excused":

        excused.add(name)

        registered.pop(uid, None)

        readers.discard(name)

        listeners.discard(name)

    elif data == "toggle":

        registration_open = not registration_open

    # ===== تحديث القائمة =====
    await q.edit_message_text(
        build_text(),
        reply_markup=menu()
    )

# ===== أخطاء =====
async def error_handler(update, context):

    print("ERROR:", context.error)

# ===== تشغيل =====
app = Application.builder().token(TOKEN).build()

app.add_handler(
    CommandHandler("start", start)
)

app.add_handler(
    CallbackQueryHandler(buttons)
)

app.add_error_handler(error_handler)

print("BOT RUNNING ✔")

# 🔥 حل مشكلة التعارض
app.run_polling(
    drop_pending_updates=True
)
