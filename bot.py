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
registered = set()
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

    # توقيت مكة
    tz = pytz.timezone("Asia/Riyadh")

    date_str = datetime.now(tz).strftime(
        "%Y-%m-%d %H:%M"
    )

    status = "🔓 مفتوح" if registration_open else "🔒 مغلق"

    text = (

        "السلام عليكم ورحمة الله وبركاته 🌿\n\n"

        f"📅 {date_str}\n\n"

        "خادم القرآن الرقمي 💫\n\n"

        f"التسجيل {status}\n\n"

        "قائمة تسجيل الأدوار 📝\n\n"

        "✍️ المسجلات:\n"
        + ("\n".join(registered)
           if registered else "لا يوجد")
        + "\n\n"

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
    # منع المحظورين
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

        # تصفير
        if query.data == "reset":

            registered.clear()
            readers.clear()
            listeners.clear()
            excused.clear()

        # قفل / فتح
        elif query.data == "toggle":

            registration_open = not registration_open

        await query.edit_message_text(
            text=build_text(),
            reply_markup=menu()
        )

        return

    # =====================
    # إذا التسجيل مغلق
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

        registered.add(user_name)

        listeners.discard(user_name)
        excused.discard(user_name)

    # =====================
    # قرأت
    # =====================
    elif query.data == "read":

        if user_name in registered:

            registered.discard(user_name)

            registered.add(
                f"{user_name} ✅"
            )

    # =====================
    # مستمعة
    # =====================
    elif query.data == "listener":

        listeners.add(user_name)

        registered.discard(user_name)
        registered.discard(
            f"{user_name} ✅"
        )

        excused.discard(user_name)

    # =====================
    # معتذرة
    # =====================
    elif query.data == "excused":

        excused.add(user_name)

        registered.discard(user_name)
        registered.discard(
            f"{user_name} ✅"
        )

        listeners.discard(user_name)

    # =====================
    # حذف الاسم
    # =====================
    elif query.data == "remove":

        registered.discard(user_name)
        registered.discard(
            f"{user_name} ✅"
        )

        readers.discard(user_name)
        listeners.discard(user_name)
        excused.discard(user_name)

    # =====================
    # تحديث الرسالة
    # =====================
    await query.edit_message_text(
        text=build_text(),
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
        CallbackQueryHandler(buttons)
    )

    print("BOT RUNNING ✔")

    app.run_polling(
        drop_pending_updates=True
            )
