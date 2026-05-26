import os
from datetime import datetime
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
# TOKEN
# =========================
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise Exception("BOT_TOKEN missing")

# =========================
# DATA
# =========================
registered = []
readers = set()
listeners = set()
excused = set()
blocked = set()

registration_open = True

# =========================
# MENU
# =========================
def menu():

    keyboard = [

        [
            InlineKeyboardButton(
                "✅ قرأت",
                callback_data="read"
            ),

            InlineKeyboardButton(
                "✍️ سجل اسمي",
                callback_data="register"
            )
        ],

        [
            InlineKeyboardButton(
                "🎧 مستمعة",
                callback_data="listener"
            ),

            InlineKeyboardButton(
                "⛔️ معتذرة",
                callback_data="excused"
            )
        ],

        [
            InlineKeyboardButton(
                "🧹 تصفير",
                callback_data="reset"
            ),

            InlineKeyboardButton(
                "🔒 قفل/فتح",
                callback_data="toggle"
            )
        ],

        [
            InlineKeyboardButton(
                "❌ حذف اسمي",
                callback_data="remove"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)

# =========================
# BUILD TEXT
# =========================
def build_text():

    tz = pytz.timezone("Asia/Riyadh")

    date_str = datetime.now(tz).strftime(
        "%Y-%m-%d %H:%M"
    )

    status = "🔓 مفتوح" if registration_open else "🔒 مغلق"

    # ترقيم المسجلات
    registered_text = ""

    if registered:

        for i, name in enumerate(registered, start=1):

            if name in readers:
                registered_text += f"{i}- {name} ✅\n"
            else:
                registered_text += f"{i}- {name}\n"

    else:
        registered_text = "لا يوجد"

    text = (

        "السلام عليكم ورحمة الله وبركاته 🌿\n\n"

        f"📅 {date_str}\n\n"

        "خادم القرآن الرقمي 💫\n\n"

        f"التسجيل {status}\n\n"

        "قائمة تسجيل الأدوار 📝\n\n"

        "✍️ المسجلات:\n"
        + registered_text
        + "\n"

        "⛔️ المعتذرات:\n"
        + ("\n".join(excused)
           if excused else "لا يوجد")
        + "\n\n"

        "🎧 المستمعات:\n"
        + ("\n".join(listeners)
           if listeners else "لا يوجد")
        + "\n\n"

        "🚫 المحظورات:\n"
        + ("\n".join(blocked)
           if blocked else "لا يوجد")
        + "\n\n"

        "﴿ وَالَّذِينَ جَاهَدُوا فِينَا "
        "لَنَهْدِيَنَّهُمْ سُبُلَنَا ۚ "
        "وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ ﴾"
    )

    return text

# =========================
# ADMIN CHECK
# =========================
async def is_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        admins = await context.bot.get_chat_administrators(
            update.effective_chat.id
        )

        return any(
            admin.user.id == update.effective_user.id
            for admin in admins
        )

    except:
        return False

# =========================
# BUTTONS
# =========================
async def buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    global registration_open

    query = update.callback_query

    await query.answer()

    user_name = query.from_user.full_name

    # =====================
    # منع المحظور
    # =====================
    if user_name in blocked:

        await query.answer(
            "🚫 أنتِ محظورة",
            show_alert=True
        )

        return

    # =====================
    # أوامر الإدارة
    # =====================
    if query.data in ["reset", "toggle"]:

        if not await is_admin(update, context):

            await query.answer(
                "🚫 للمشرفات فقط",
                show_alert=True
            )

            return

        if query.data == "reset":

            registered.clear()
            readers.clear()
            listeners.clear()
            excused.clear()

        elif query.data == "toggle":

            registration_open = not registration_open

        await query.edit_message_text(
            text=build_text(),
            reply_markup=menu()
        )

        return

    # =====================
    # التسجيل مغلق
    # =====================
    if not registration_open:

        await query.answer(
            "🔒 التسجيل مغلق",
            show_alert=True
        )

        return

    # =====================
    # تسجيل
    # =====================
    if query.data == "register":

        if user_name not in registered:
            registered.append(user_name)

        listeners.discard(user_name)
        excused.discard(user_name)

    # =====================
    # قرأت
    # =====================
    elif query.data == "read":

        if user_name in registered:
            readers.add(user_name)

    # =====================
    # مستمعة
    # =====================
    elif query.data == "listener":

        listeners.add(user_name)

        if user_name in registered:
            registered.remove(user_name)

        readers.discard(user_name)
        excused.discard(user_name)

    # =====================
    # معتذرة
    # =====================
    elif query.data == "excused":

        excused.add(user_name)

        if user_name in registered:
            registered.remove(user_name)

        readers.discard(user_name)
        listeners.discard(user_name)

    # =====================
    # حذف الاسم
    # =====================
    elif query.data == "remove":

        if user_name in registered:
            registered.remove(user_name)

        readers.discard(user_name)
        listeners.discard(user_name)
        excused.discard(user_name)

    # =====================
    # تحديث
    # =====================
    await query.edit_message_text(
        text=build_text(),
        reply_markup=menu()
    )

# =========================
# BAN
# =========================
async def ban(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not await is_admin(update, context):
        return

    if update.message.reply_to_message:

        user_name = update.message.reply_to_message.from_user.full_name

        blocked.add(user_name)

        if user_name in registered:
            registered.remove(user_name)

        readers.discard(user_name)
        listeners.discard(user_name)
        excused.discard(user_name)

        await update.message.reply_text(
            build_text(),
            reply_markup=menu()
        )

# =========================
# UNBAN
# =========================
async def unban(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not await is_admin(update, context):
        return

    if update.message.reply_to_message:

        user_name = update.message.reply_to_message.from_user.full_name

        blocked.discard(user_name)

        await update.message.reply_text(
            build_text(),
            reply_markup=menu()
        )

# =========================
# START
# =========================
async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        build_text(),
        reply_markup=menu()
    )

# =========================
# MAIN
# =========================
if __name__ == "__main__":

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

    print("BOT RUNNING ✔")

    app.run_polling(
        drop_pending_updates=True
        )
