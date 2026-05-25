import os
import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise Exception("BOT_TOKEN missing")

# ===== البيانات =====
registered = {}
readers = set()
listeners = set()
excused = set()
blocked = {}

registration_open = True

# ===== الوقت =====
def now():
    tz = pytz.timezone("Asia/Riyadh")
    return datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M")

# ===== تنسيق المسجلات بدون أخطاء =====
def format_registered():
    if not registered:
        return "لا يوجد"

    text = ""
    for uid, name in registered.items():
        mark = "✅️" if name in readers else ""
        text += f"• {name} {mark}\n"
    return text.strip()

# ===== القائمة =====
def build_text():
    lock = "🔓 التسجيل مفتوح" if registration_open else "🔒 التسجيل مغلق"

    return f"""
السلام عليكم ورحمة الله وبركاته 🌿

خادم القرآن الرقمي 🤍
📅 {now()}

{lock}

📌 قائمة تسجيل الأدوار

✍️ المسجلات:
{format_registered()}

🎧 المستمعات:
{chr(10).join(list(listeners)) or "لا يوجد"}

⛔️ المعتذرات:
{chr(10).join(list(excused)) or "لا يوجد"}

🚫 المحظورات:
{chr(10).join(list(blocked.values())) or "لا يوجد"}

﴿ وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ۚ وَإِنَّ اللَّهَ لَمَعُ الْمُحْسِنِينَ ﴾
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
            InlineKeyboardButton("🚫 محظورات", callback_data="show"),
            InlineKeyboardButton("🔒 قفل/فتح", callback_data="toggle")
        ],
        [
            InlineKeyboardButton("🧹 تصفير", callback_data="reset")
        ]
    ])

# ===== start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = """
🌿 أهلاً بك في خادم القرآن الرقمي 🤍

📌 الوظائف:
• تسجيل الأدوار
• متابعة القراءة
• إدارة الحالات
• عرض المحظورات
• منع الروابط

🤍 اللهم اجعل أعمالنا خالصة لوجهك الكريم
"""
    await update.message.reply_text(msg, reply_markup=menu())

# ===== حظر =====
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global blocked

    if not update.message.reply_to_message:
        await update.message.reply_text("❗ رد على رسالة الطالبة ثم /ban")
        return

    user = update.message.reply_to_message.from_user
    uid = user.id
    name = user.first_name

    blocked[uid] = name

    registered.pop(uid, None)
    readers.discard(name)
    listeners.discard(name)
    excused.discard(name)

    await update.message.reply_text(f"🚫 تم حظر {name}")

# ===== فك حظر =====
async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global blocked

    if not update.message.reply_to_message:
        await update.message.reply_text("❗ رد على رسالة الطالبة ثم /unban")
        return

    user = update.message.reply_to_message.from_user
    uid = user.id
    name = user.first_name

    if uid not in blocked:
        await update.message.reply_text("ℹ️ ليست محظورة")
        return

    blocked.pop(uid, None)
    await update.message.reply_text(f"✅ تم فك الحظر عن {name}")

# ===== الأزرار =====
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global registration_open

    q = update.callback_query
    await q.answer()

    user = q.from_user
    uid = user.id
    name = user.first_name

    if uid in blocked:
        await q.edit_message_text("🚫 أنتِ محظورة")
        return

    data = q.data

    if data == "reg":
        if not registration_open:
            await q.edit_message_text("🔒 التسجيل مغلق")
            return
        registered[uid] = name

    elif data == "read":
        if uid in registered:
            readers.add(name)

    elif data == "listen":
        listeners.add(name)
        registered.pop(uid, None)
        readers.discard(name)
        excused.discard(name)

    elif data == "excused":
        excused.add(name)
        registered.pop(uid, None)
        readers.discard(name)
        listeners.discard(name)

    elif data == "toggle":
        registration_open = not registration_open

    elif data == "reset":
        registered.clear()
        readers.clear()
        listeners.clear()
        excused.clear()

    await q.edit_message_text(build_text(), reply_markup=menu())

# ===== منع الروابط =====
async def block_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private":
        return

    if update.message.entities:
        for e in update.message.entities:
            if e.type == "url":
                await update.message.delete()
                await update.message.reply_text("⛔️ الروابط ممنوعة")
                return

# ===== تشغيل =====
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ban", ban))
app.add_handler(CommandHandler("unban", unban))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, block_links))

print("BOT STARTED ✔")
app.run_polling()
