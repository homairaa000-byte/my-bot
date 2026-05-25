import os
import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise Exception("BOT_TOKEN missing")

registered = {}
readers = set()
listeners = set()
excused = set()
blocked = {}

registration_open = True

def now():
    return datetime.datetime.now(pytz.timezone("Asia/Riyadh")).strftime("%Y-%m-%d %H:%M")

def format_list():
    if not registered:
        return "لا يوجد"
    return "\n".join([f"• {name}" for name in registered.values()])

def build_text():
    lock = "🔓 مفتوح" if registration_open else "🔒 مغلق"

    return f"""
السلام عليكم ورحمة الله وبركاته 🌿

خادم القرآن الرقمي 🤍
📅 {now()}

{lock}

✍️ المسجلات:
{format_list()}

﴿ وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ﴾
"""

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ سجل", callback_data="reg")],
        [InlineKeyboardButton("📖 قرأت", callback_data="read")],
        [InlineKeyboardButton("🎧 مستمعة", callback_data="listen")],
        [InlineKeyboardButton("⛔ معتذرة", callback_data="excused")],
        [InlineKeyboardButton("🔒 قفل/فتح", callback_data="toggle")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(build_text(), reply_markup=menu())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global registration_open

    q = update.callback_query
    await q.answer()

    user = q.from_user
    uid = user.id
    name = user.first_name

    if uid in blocked:
        await q.answer("🚫 محظورة", show_alert=True)
        return

    data = q.data

    # 🔒 القفل الحقيقي بدون كسر الرسالة
    if not registration_open and data in ["reg", "read", "listen", "excused"]:
        await q.answer("🔒 التسجيل مغلق", show_alert=True)
        return

    if data == "reg":
        registered[uid] = name

    elif data == "read":
        if uid in registered:
            readers.add(name)

    elif data == "listen":
        listeners.add(name)
        registered.pop(uid, None)

    elif data == "excused":
        excused.add(name)
        registered.pop(uid, None)

    elif data == "toggle":
        registration_open = not registration_open

    await q.edit_message_text(build_text(), reply_markup=menu())

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))

print("BOT RUNNING")
app.run_polling()
