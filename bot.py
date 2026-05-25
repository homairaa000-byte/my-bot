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
registered = {}   # user_id -> name
readers = set()
listeners = set()
excused = set()
blocked = set()

registration_open = True

# ===== الوقت =====
def makkah_time():
    tz = pytz.timezone("Asia/Riyadh")
    return datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M")

# ===== اسم المستخدم الحقيقي =====
def get_name(user):
    return user.first_name

# ===== بناء القائمة =====
def build_text():
    lock_icon = "🔓 التسجيل مفتوح" if registration_open else "🔒 التسجيل مغلق"

    return f"""
السلام عليكم ورحمة الله وبركاته 🌿

خادم القرآن الرقمي 🤍
📅 {makkah_time()}

{lock_icon}

📌 قائمة تسجيل الأدوار

✍️ المسجلات:
{chr(10).join([f"• {name} {'✅️' if name in readers else ''}" for name in registered.values()]) or "لا يوجد"}

🎧 المستمعات:
{chr(10).join(list(listeners)) or "لا يوجد"}

⛔️ المعتذرات:
{chr(10).join(list(excused)) or "لا يوجد"}

🚫 المحظورات:
{chr(10).join(list(blocked)) or "لا يوجد"}

﴿ وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ۚ وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ ﴾
"""

# ===== الأزرار =====
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
            InlineKeyboardButton("🔒 قفل/فتح", callback_data="toggle"),
            InlineKeyboardButton("🚫 محظورات", callback_data="show")
        ],
        [
            InlineKeyboardButton("🧹 تصفير", callback_data="reset")
        ]
    ])

# ===== start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(build_text(), reply_markup=menu())

# ===== الأزرار =====
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global registration_open

    q = update.callback_query
    await q.answer()

    user = q.from_user
    user_id = user.id
    name = get_name(user)

    if user_id in blocked:
        await q.edit_message_text("⛔ أنتِ محظورة")
        return

    data = q.data

    # تسجيل
    if data == "reg":
        if not registration_open:
            await q.edit_message_text("⛔ التسجيل مغلق")
            return
        registered[user_id] = name
        await q.edit_message_text(build_text(), reply_markup=menu())

    # قرأت
    elif data == "read":
        registered[user_id] = name
        readers.add(name)

        listeners.discard(name)
        excused.discard(name)

        await q.edit_message_text(build_text(), reply_markup=menu())

    # مستمعة
    elif data == "listen":
        listeners.add(name)

        readers.discard(name)
        excused.discard(name)

        registered.pop(user_id, None)

        await q.edit_message_text(build_text(), reply_markup=menu())

    # معتذرة
    elif data == "excused":
        excused.add(name)

        readers.discard(name)
        listeners.discard(name)

        registered.pop(user_id, None)

        await q.edit_message_text(build_text(), reply_markup=menu())

    # قفل/فتح
    elif data == "toggle":
        registration_open = not registration_open
        await q.edit_message_text(build_text(), reply_markup=menu())

    # محظورات
    elif data == "show":
        await q.edit_message_text(build_text(), reply_markup=menu())

    # تصفير
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

    if update.message.entities:
        for e in update.message.entities:
            if e.type == "url":
                await update.message.delete()
                await update.message.reply_text("⛔️ إرسال الروابط ممنوع")
                return

# ===== التشغيل =====
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, block_links))

print("BOT STARTED ✔")
app.run_polling()
