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
registered = {}   # uid -> name
readers = set()
listeners = set()
excused = set()
blocked = {}      # uid -> name

registration_open = True

# ===== الوقت =====
def now():
    tz = pytz.timezone("Asia/Riyadh")
    return datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M")

# ===== الاسم =====
def get_name(user):
    return user.first_name

# ===== بناء القائمة =====
def build_text():

    lock = "🔓 التسجيل مفتوح" if registration_open else "🔒 التسجيل مغلق"

    return f"""
السلام عليكم ورحمة الله وبركاته 🌿

خادم القرآن الرقمي 🤍
📅 {now()}

{lock}

📌 قائمة تسجيل الأدوار

✍️ المسجلات:
{chr(10).join([f"• [{name}](tg://user?id={uid}) {'✅️' if name in readers else ''}" for uid, name in registered.items()]) or "لا يوجد"}

🎧 المستمعات:
{chr(10).join(list(listeners)) or "لا يوجد"}

⛔️ المعتذرات:
{chr(10).join(list(excused)) or "لا يوجد"}

🚫 المحظورات:
{chr(10).join([f"• {name}" for name in blocked.values()]) or "لا يوجد"}

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
    text = """
🌿 أهلاً بك في خادم القرآن الرقمي 🤍

📌 الوظائف:
• تسجيل الأدوار
• متابعة القراءة
• تنظيم المستمعات والمعتذرات
• إدارة المحظورات

✨ استخدمي الأزرار بالأسفل

🤍 اللهم اجعل أعمالنا خالصة لوجهك الكريم
"""
    await update.message.reply_text(text, reply_markup=menu(), parse_mode="Markdown")

# ===== الحظر =====
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
    await update.message.reply_text(build_text(), reply_markup=menu(), parse_mode="Markdown")

# ===== فك الحظر =====
async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global blocked

    if not update.message.reply_to_message:
        await update.message.reply_text("❗ رد على رسالة الطالبة ثم /unban")
        return

    user = update.message.reply_to_message.from_user
    uid = user.id
    name = user.first_name

    if uid not in blocked:
        await update.message.reply_text("ℹ️ هذه الطالبة ليست محظورة")
        return

    blocked.pop(uid, None)

    await update.message.reply_text(f"✅ تم فك الحظر عن {name}")
    await update.message.reply_text(build_text(), reply_markup=menu(), parse_mode="Markdown")

# ===== الأزرار =====
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global registration_open

    q = update.callback_query
