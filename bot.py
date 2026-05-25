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
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise Exception("BOT_TOKEN missing")

# =========================
DATA
# =========================
registered = {}
readers = set()
listeners = set()
excused = set()
blocked = {}

registration_open = True

ADMIN_IDS = set()  # ضع/ي ايدي المشرفات هنا

# =========================
TIME
# =========================
def now():
    tz = pytz.timezone("Asia/Riyadh")
    return datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M")

# =========================
TEXT BUILD
# =========================
def build_text():

    status = "🔓 التسجيل مفتوح" if registration_open else "🔒 التسجيل مغلق"

    return (
        "السلام عليكم ورحمة الله وبركاته 🌿\n\n"
        "خادم القرآن الرقمي 🤍\n"
        f"📅 {now()}\n\n"
        f"{status}\n\n"

        "📌 قائمة تسجيل الأدوار\n\n"

        "✍️ المسجلات:\n" +
        ("\n".join([f"• {n}" for n in registered.values()]) or "لا يوجد") + "\n\n"

        "🎧 المستمعات:\n" +
        ("\n".join(listeners) or "لا يوجد") + "\n\n"

        "⛔️ المعتذرات:\n" +
        ("\n".join(excused) or "لا يوجد") + "\n\n"

        "🚫 المحظورات:\n" +
        ("\n".join(blocked.values()) or "لا يوجد") + "\n\n"

        "﴿ وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ﴾"
    )

# =========================
MENU
# =========================
def menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✍️ سجل", callback_data="reg"),
            InlineKeyboardButton("📖 قرأت", callback_data="read")
        ],
        [
            InlineKeyboardButton("🎧 مستمعة", callback_data="listen"),
            InlineKeyboardButton("⛔ معتذرة", callback_data="excused")
        ],
        [
            InlineKeyboardButton("🔒 قفل/فتح", callback_data="toggle"),
            InlineKeyboardButton("🧹 تصفير", callback_data="reset")
        ]
    ])

# =========================
START (خاص)
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_chat.type != "private":
        return  # لا يرسل في المجموعات

    await update.message.reply_text(
        "🌿 أهلاً بك في خادم القرآن الرقمي 🤍\n\n"
        "📌 طريقة الاستخدام:\n"
        "• سجل إسمي → تسجيل\n"
        "• قرأت → تأكيد القراءة\n"
        "• مستمعة / معتذرة\n"
        "• القوائم تتحدث للجميع مباشرة\n\n"
        "🤍 اللهم اجعل أعمالنا خالصة لوجهك الكريم"
    )

    await update.message.reply_text(
        build_text(),
        reply_markup=menu()
    )

# =========================
LINK FILTER
# =========================
async def block_links(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.message.from_user

    if user.id in ADMIN_IDS:
        return

    text = update.message.text or ""

    if "http" in text or "www" in text:

        await update.message.delete()

        await update.message.reply_text(
            "🚫🚫🚫 إرسال رابط من غير إذن الإشراف يعرضك للحذف أو الحظر"
        )

# =========================
BUTTONS
# =========================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global registration_open

    q = update.callback_query
    await q.answer()

    user = q.from_user
    uid = user.id
    name = user.first_name

    if uid in blocked:
        await q.answer("🚫 أنتِ محظورة", show_alert=True)
        return

    # إذا مغلق لا يختفي ولا يغير شيء
    if not registration_open and q.data in ["reg", "read", "listen", "excused"]:
        await q.answer("🔒 التسجيل مغلق", show_alert=True)
        return

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

    elif q.data == "toggle":
        registration_open = not registration_open

    elif q.data == "reset":
        registered.clear()
        readers.clear()
        listeners.clear()
        excused.clear()

    await q.edit_message_text(build_text(), reply_markup=menu())

# =========================
BAN
# =========================
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message.reply_to_message:
        return

    user = update.message.reply_to_message.from_user

    blocked[user.id] = user.first_name

    registered.pop(user.id, None)

    await update.message.reply_text(f"🚫 تم حظر {user.first_name}")

# =========================
APP
# =========================
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ban", ban))

app.add_handler(CallbackQueryHandler(buttons))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, block_links))

print("
