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

# =========================
# BOT TOKEN
# =========================
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise Exception("BOT_TOKEN missing")

# =========================
# DATA
# =========================
registered = {}
readers = set()
listeners = set()
excused = set()
blocked = {}

registration_open = True

# =========================
# TIME
# =========================
def now():
    tz = pytz.timezone("Asia/Riyadh")
    return datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M")

# =========================
# REGISTERED FORMAT
# =========================
def format_registered():

    if not registered:
        return "لا يوجد"

    text = ""

    for uid, name in registered.items():

        mark = ""

        if name in readers:
            mark = " ✅️"

        text += f"• {name}{mark}\n"

    return text.strip()

# =========================
# LIST BUILD
# =========================
def build_text():

    status = "🔓 التسجيل مفتوح"

    if not registration_open:
        status = "🔒 التسجيل مغلق"

    listeners_text = "\n".join(listeners) if listeners else "لا يوجد"

    excused_text = "\n".join(excused) if excused else "لا يوجد"

    blocked_text = (
        "\n".join(blocked.values())
        if blocked else "لا يوجد"
    )

    text = (
        "السلام عليكم ورحمة الله وبركاته 🌿\n\n"

        "خادم القرآن الرقمي 🤍\n"

        f"📅 {now()}\n\n"

        f"{status}\n\n"

        "📌 قائمة تسجيل الأدوار\n\n"

        "✍️ المسجلات:\n"
        f"{format_registered()}\n\n"

        "🎧 المستمعات:\n"
        f"{listeners_text}\n\n"

        "⛔️ المعتذرات:\n"
        f"{excused_text}\n\n"

        "🚫 المحظورات:\n"
        f"{blocked_text}\n\n"

        "﴿ وَالَّذِينَ جَاهَدُوا فِينَا "
        "لَنَهْدِيَنَّهُمْ سُبُلَنَا ۚ "
        "وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ ﴾"
    )

    return text

# =========================
# BUTTONS
# =========================
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
                "🔒 قفل / فتح التسجيل",
                callback_data="toggle"
            )
        ],

        [
            InlineKeyboardButton(
                "🧹 تصفير القائمة",
                callback_data="reset"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)

# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    welcome = (
        "🌿 أهلاً بك في خادم القرآن الرقمي 🤍\n\n"

        "📌 وظائف البوت:\n"
        "• تنظيم تسجيل الأدوار\n"
        "• متابعة القراءة\n"
        "• تنظيم المستمعات والمعتذرات\n"
        "• إدارة المحظورات\n\n"

        "🤍 اللهم اجعل أعمالنا خالصة لوجهك الكريم"
    )

    await update.message.reply_text(welcome)

    await update.message.reply_text(
        build_text(),
        reply_markup=menu()
    )

# =========================
# BUTTONS ACTION
# =========================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global registration_open

    q = update.callback_query

    await q.answer()

    user = q.from_user

    uid = user.id
    name = user.first_name

    # =========================
    # BLOCKED CHECK
    # =========================
    if uid in blocked:

        await q.answer(
            "🚫 أنتِ محظورة",
            show_alert=True
        )

        return

    data = q.data

    # =========================
    # CLOSED REGISTRATION
    # =========================
    if (
        not registration_open
        and data in ["reg", "read", "listen", "excused"]
    ):

        await q.answer(
            "🔒 التسجيل مغلق حالياً",
            show_alert=True
        )

        return

    # =========================
    # REGISTER
    # =========================
    if data == "reg":

        registered[uid] = name

        listeners.discard(name)
        excused.discard(name)

    # =========================
    # READ
    # =========================
    elif data == "read":

        if uid in registered:
            readers.add(name)

    # =========================
    # LISTENER
    # =========================
    elif data == "listen":

        listeners.add(name)

        registered.pop(uid, None)

        readers.discard(name)

        excused.discard(name)

    # =========================
    # EXCUSED
    # =========================
    elif data == "excused":

        excused.add(name)

        registered.pop(uid, None)

        readers.discard(name)

        listeners.discard(name)

    # =========================
    # TOGGLE
    # =========================
    elif data == "toggle":

        registration_open = not registration_open

    # =========================
    # RESET
    # =========================
    elif data == "reset":

        registered.clear()

        readers.clear()

        listeners.clear()

        excused.clear()

    # =========================
    # UPDATE MESSAGE
    # =========================
    await q.edit_message_text(
        build_text(),
        reply_markup=menu()
    )

# =========================
# BAN
# =========================
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message.reply_to_message:

        await update.message.reply_text(
            "❗ قومي بالرد على رسالة الطالبة ثم استخدمي /ban"
        )

        return

    user = update.message.reply_to_message.from_user

    uid = user.id
    name = user.first_name

    blocked[uid] = name

    registered.pop(uid, None)

    readers.discard(name)

    listeners.discard(name)

    excused.discard(name)

    await update.message.reply_text(
        f"🚫 تم حظر {name}"
    )

# =========================
# UNBAN
# =========================
async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message.reply_to_message:

        await update.message.reply_text(
            "❗ قومي بالرد على رسالة الطالبة ثم استخدمي /unban"
        )

        return

    user = update.message.reply_to_message.from_user

    uid = user.id
    name = user.first_name

    if uid in blocked:

        blocked.pop(uid)

        await update.message.reply_text(
            f"✅ تم فك الحظر عن {name}"
        )

# =========================
# ERROR HANDLER
# =========================
async def error_handler(update, context):

    print("ERROR:", context.error)

# =========================
# APP
# =========================
app = Application.builder().token(TOKEN).build()

app.add_handler(
    CommandHandler("start", start)
)

app.add_handler(
    CommandHandler("ban", ban)
)

app.add_handler(
    CommandHandler("unban", unban)
)

app.add_handler(
    CallbackQueryHandler(buttons)
)

app.add_error_handler(error_handler)

print("BOT RUNNING ✔")

# =========================
# RUN
# =========================
app.run_polling(
    drop_pending_updates=True
)
