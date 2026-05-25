import os
import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise Exception("BOT_TOKEN missing")

# ====== البيانات ======
students = {}
blocked = set()
registration_open = True

# ====== الوقت مكة ======
def makkah_time():
    tz = pytz.timezone("Asia/Riyadh")
    return datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M")

# ====== لوحة التحكم ======
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍ سجل إسمي", callback_data="reg")],
        [InlineKeyboardButton("✅ قرأت", callback_data="read")],
        [InlineKeyboardButton("🎧 مستمعات", callback_data="listen")],
        [InlineKeyboardButton("⛔ معتذرات", callback_data="excused")],
        [InlineKeyboardButton("🚫 محظورات", callback_data="blocked")],
        [InlineKeyboardButton("❌ إحذف إسمي", callback_data="delete")],
        [InlineKeyboardButton("🔒 قفل/فتح التسجيل", callback_data="toggle")],
        [InlineKeyboardButton("🧹 تصفير", callback_data="reset")]
    ])

# ====== بدء ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = f"""
السلام عليكم ورحمة الله وبركاته 🌿

﴿ وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ﴾

خادم القرآن الرقمي 🤍
📅 {makkah_time()}
"""
    await update.message.reply_text(text, reply_markup=menu())

# ====== تسجيل ======
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global registration_open

    q = update.callback_query
    user = q.from_user.username or q.from_user.first_name
    await q.answer()

    if user in blocked:
        await q.edit_message_text("⛔ أنتِ محظورة")
        return

    data = q.data

    if data == "reg":
        if not registration_open:
            await q.edit_message_text("⛔ التسجيل مغلق")
            return
        students[user] = "joined"
        await q.edit_message_text(f"✔ تم تسجيل {user}")

    elif data == "read":
        students[user] = "read"
        await q.edit_message_text(f"📖 تم تسجيل قراءة {user}")

    elif data == "listen":
        students[user] = "listen"
        await q.edit_message_text(f"🎧 تم نقل {user} للمستمعات")

    elif data == "excused":
        students[user] = "excused"
        await q.edit_message_text(f"⛔ تم تسجيل {user} معتذرة")

    elif data == "blocked":
        students[user] = "blocked"
        await q.edit_message_text(f"🚫 تم تسجيل {user} محظورة")

    elif data == "delete":
        students.pop(user, None)
        await q.edit_message_text(f"❌ تم حذف {user}")

    elif data == "toggle":
        registration_open = not registration_open
        status = "مفتوح" if registration_open else "مغلق"
        await q.edit_message_text(f"🔒 حالة التسجيل: {status}")

    elif data == "reset":
        students.clear()
        await q.edit_message_text("🧹 تم تصفير القائمة")

# ====== منع الروابط ======
async def block_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private":
        return

    if update.message.from_user.is_bot:
        return

    user = update.message.from_user.username or ""

    if update.message.entities:
        for e in update.message.entities:
            if e.type == "url":
                await update.message.delete()
                await update.message.reply_text(
                    "⛔️⛔️⛔️ إرسال روابط من دون الرجوع للإشراف يعرضك للحذف"
                )
                return

# ====== حظر بالرد ======
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return

    user = update.message.reply_to_message.from_user.username or update.message.reply_to_message.from_user.first_name
    blocked.add(user)
    students.pop(user, None)

    await update.message.reply_text(f"🚫 تم حظر {user}")

# ====== تشغيل ======
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ban", ban))
app.add_handler(CallbackQueryHandler(handle_buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, block_links))

print("BOT STARTED ✔")
app.run_polling()
