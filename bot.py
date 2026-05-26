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
    MessageHandler,
    ContextTypes,
    filters
)

# =========================
# TOKEN
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
# ADMIN CHECK
# =========================
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id,
            user_id
        )

        return member.status in ["administrator", "creator"]

    except:
        return False

# =========================
# BUILD TEXT
# =========================
def build_text():

    status = "🔓 التسجيل مفتوح" if registration_open else "🔒 التسجيل مغلق"

    registered_names = "\n".join(
        [f"• {n}" for n in registered.values()]
    ) or "لا يوجد"

    listeners_names = "\n".join(listeners) or "لا يوجد"

    excused_names = "\n".join(excused) or "لا يوجد"

    blocked_names = "\n".join(blocked.values()) or "لا يوجد"

    return (
        "السلام عليكم ورحمة الله وبركاته 🌿\n\n"
        "خادم القرآن الرقمي 🤍\n"
        f"📅 {now()}\n\n"
        f"{status}\n\n"

        "📌 قائمة تسجيل الأدوار\n\n"

        "✍️ المسجلات:\n"
        f"{registered_names}\n\n"

        "🎧 المستمعات:\n"
        f"{listeners_names}\n\n"

        "⛔️ المعتذرات:\n"
        f"{excused_names}\n\n"

        "🚫 المحظورات:\n"
        f"{blocked_names}\n\n"

        "﴿ وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ﴾"
    )

# =========================
# BUTTONS
# =========================
def menu():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "✍️ سجل",
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
                "🔒 قفل/فتح",
                callback_data="toggle"
            ),

            InlineKeyboardButton(
                "🧹 تصفير",
                callback_data="reset"
            )
        ]
    ])

# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        build_text(),
        reply_markup=menu()
    )

# =========================
# BUTTONS HANDLER
# =========================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global registration_open

    q = update.callback_query

    await q.answer()

    uid = q.from_user.id
    name = q.from_user.first_name

    # =====================
    # BLOCKED CHECK
    # =====================
    if uid in blocked:

        await q.answer(
            "🚫 أنتِ محظورة",
            show_alert=True
        )

        return

    # =====================
    # ADMIN BUTTONS
    # =====================
    if q.data in ["toggle", "reset"]:

        if not await is_admin(update, context, uid):

            await q.answer(
                "🚫 هذه الصلاحية للمشرفات فقط",
                show_alert=True
            )

            return

        if q.data == "toggle":

            registration_open = not registration_open

        elif q.data == "reset":

            registered.clear()
            readers.clear()
            listeners.clear()
            excused.clear()

    # =====================
    # NORMAL ACTIONS
    # =====================
    elif registration_open:

        if q.data == "reg":

            registered[uid] = name

        elif q.data == "read":

            if uid in registered:
                readers.add(name)

        elif q.data == "listen":

            listeners.add(name)
            registered.pop(uid, None)

        elif q.data == "excused":

            excused.add(name)
            registered.pop(uid, None)

    else:

        await q.answer(
            "🔒 التسجيل مغلق",
            show_alert=True
        )

        return

    # =====================
    # UPDATE MESSAGE
    # =====================
    await q.edit_message_text(
        build_text(),
        reply_markup=menu()
    )

# =========================
# BLOCK LINKS
# =========================
async def block_links(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if await is_admin(
        update,
        context,
        update.message.from_user.id
    ):
        return

    text = (update.message.text or "").lower()

    if (
        "http" in text
        or "https" in text
        or "www" in text
        or "t.me" in text
    ):

        try:
            await update.message.delete()
        except:
            pass

        await update.message.reply_text(
            "🚫🚫🚫 إرسال الروابط غير مسموح"
        )

# =========================
# BAN USER
# =========================
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(
        update,
        context,
        update.message.from_user.id
    ):
        return

    if update.message.reply_to_message:

        user = update.message.reply_to_message.from_user

        blocked[user.id] = user.first_name

        registered.pop(user.id, None)

        await update.message.reply_text(
            f"🚫 تم حظر {user.first_name}"
        )

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
    CallbackQueryHandler(buttons)
)

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        block_links
    )
)

print("BOT RUNNING ✔")

app.run_polling(
    drop_pending_updates=True
)
