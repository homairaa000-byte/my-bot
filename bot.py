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

# ===== البيانات =====
registered = {}
readers = set()
listeners = set()
excused = set()
blocked = set()

registration_open = True

# ===== الوقت =====
def makkah_time():
    tz = pytz.timezone("Asia/Riyadh")
    return datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M")

# ===== بناء القائمة =====
def build_text():
    text = f"""
السلام عليكم ورحمة الله وبركاته 🌿

خادم القرآن الرقمي 🤍
📅 {makkah_time()}

📌 قائمة تسجيل الأدوار

✍️ المسجلات:
{chr(10).join([f"• {u} {'✅️' if u in readers else ''}" for u in registered]) or "لا يوجد"}

🎧 المستمعات:
{chr(10).join(list(listeners)) or "لا يوجد"}

⛔️ المعتذرات:
{chr(10).join(list(excused)) or "لا يوجد"}

🚫 المحظورات:
{chr(10).join(list(blocked)) or "لا يوجد"}

﴿ وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ۚ وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ ﴾
"""
    return text

# ===== لوحة الأزرار =====
def menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✍️ سجل إسمي", callback_data="reg"),
            InlineKeyboardButton("📖 قرأت", callback_data="read")
        ],
        [
            InlineKeyboardButton("🎧 مستمعة", callback_data="listen"),
            InlineKeyboardButton("⛔ معتذرة", callback_data="excused")
        ],
        [
            InlineKeyboardButton("🚫 المحظورات", callback_data="show_blocked"),
            InlineKeyboardButton("🔒 قفل/فتح", callback_data="toggle")
        ],
        [
            InlineKeyboardButton("🧹 تصفير", callback_data="reset")
        ]
    ])

# ===== /start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(build_text(), reply_markup=menu())

# ===== الأزرار =====
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global registration_open

    q = update.callback_query
    await q.answer()

    user = q.from_user.username or q.from_user.first_name

    if user in blocked:
        await q.edit_message_text("⛔ أنتِ محظورة")
        return

    data = q.data

    # تسجيل
    if data == "reg":
        if not registration_open:
            await q.edit_message_text("⛔ التسجيل مغلق")
            return
        registered[user] = True
        await q.edit_message_text(build_text(), reply_markup=menu())

    elif data == "read":
        readers.add(user)
        registered[user] = True
        await q.edit_message_text(build_text(), reply_markup=menu())

    elif data == "listen":
        listeners.add(user)
        excused.discard(user)
        await q.edit_message_text(build_text(), reply_markup=menu())

    elif data == "excused":
        excused.add(user)
        listeners.discard(user)
        await q.edit_message_text(build_text(), reply_markup=menu())

    elif data == "show_blocked":
        await q.edit_message_text(build_text(), reply_markup=menu())

    elif data == "toggle":
        global registration_open
        registration_open = not registration_open
        await q.edit_message_text(build_text(), reply_markup=menu())

    elif data == "reset":
        registered.clear()
        readers.clear()
        listeners.clear()
        excused.clear()
        await q.edit_message_text("🧹 تم تصفير القائمة")

# ===== منع الروابط =====
async def block_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private":
        return

    user = update.message.from_user.username or update.message.from_user.first_name

    if update.message.entities:
        for e in update.message.entities:
            if e.type == "url":
                await update.message.delete()
                await update.message.reply_text("⛔️ إرسال روابط ممنوع وسيتم اتخاذ إجراء")
                return

# ===== التشغيل =====
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, block_links))

print("BOT STARTED ✔")
app.run_polling()
