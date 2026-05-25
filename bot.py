import os
import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

print("🔥 BOT FILE STARTED")

TOKEN = os.getenv("BOT_TOKEN")
print("TOKEN:", "OK" if TOKEN else "MISSING")

if not TOKEN:
    raise Exception("BOT_TOKEN missing")

students = {}
blocked = set()
registration_open = True

def makkah_time():
    tz = pytz.timezone("Asia/Riyadh")
    return datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M")

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = f"""
السلام عليكم ورحمة الله وبركاته 🌿

﴿ وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ﴾

📅 {makkah_time()}
"""
    await update.message.reply_text(text, reply_markup=menu())

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global registration_open

    q = update.callback_query
    await q.answer()

    user = q.from_user.username or q.from_user.first_name

    if user in blocked:
        await q.edit_message_text("⛔ أنتِ محظورة")
        return

    data = q.data

    if data == "reg":
        students[user] = "joined"
        await q.edit_message_text(f"✔ تم تسجيل {user}")

    elif data == "read":
        students[user] = "read"
        await q.edit_message_text(f"📖 تم تسجيل القراءة")

    elif data == "listen":
        students[user] = "listen"
        await q.edit_message_text(f"🎧 تم نقلك للمستمعات")

    elif data == "excused":
        students[user] = "excused"
        await q.edit_message_text(f"⛔ معتذرة")

    elif data == "blocked":
        students[user] = "blocked"
        await q.edit_message_text(f"🚫 محظورة")

    elif data == "delete":
        students.pop(user, None)
        await q.edit_message_text("❌ تم حذفك")

    elif data == "toggle":
        global registration_open
        registration_open = not registration_open
        status = "مفتوح" if registration_open else "مغلق"
        await q.edit_message_text(f"🔒 التسجيل: {status}")

    elif data == "reset":
        students.clear()
        await q.edit_message_text("🧹 تم التصفير")

async def block_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private":
        return

    if update.message.entities:
        for e in update.message.entities:
            if e.type == "url":
                await update.message.delete()
                await update.message.reply_text("⛔ الروابط ممنوعة")
                return

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return

    user = update.message.reply_to_message.from_user.username or update.message.reply_to_message.from_user.first_name
    blocked.add(user)
    students.pop(user, None)

    await update.message.reply_text(f"🚫 تم حظر {user}")

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ban", ban))
app.add_handler(CallbackQueryHandler(handle_buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, block_links))

print("BOT STARTED ✔")
app.run_polling()
