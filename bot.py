import os
from datetime import datetime
import pytz

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise Exception("BOT_TOKEN missing")

# =========================
# DATA STORAGE (لكل مجموعة بياناتها)
# =========================
chat_data = {}

def get_data(chat_id):
    if chat_id not in chat_data:
        chat_data[chat_id] = {
            "registered": [],
            "readers": set(),
            "listeners": set(),
            "excused": set(),
            "blocked": set(),
            "registration_open": True
        }
    return chat_data[chat_id]

# =========================
# MENU
# =========================
def menu():
    keyboard = [
        [InlineKeyboardButton("✅ قرأت", callback_data="read"),
         InlineKeyboardButton("✍️ سجل اسمي", callback_data="register")],
        [InlineKeyboardButton("🎧 مستمعة", callback_data="listener"),
         InlineKeyboardButton("⛔️ معتذرة", callback_data="excused")],
        [InlineKeyboardButton("🧹 تصفير", callback_data="reset"),
         InlineKeyboardButton("🔒 قفل/فتح", callback_data="toggle")],
        [InlineKeyboardButton("❌ حذف اسمي", callback_data="remove")]
    ]
    return InlineKeyboardMarkup(keyboard)

# =========================
# BUILD TEXT
# =========================
def build_text(chat_id):
    data = get_data(chat_id)
    tz = pytz.timezone("Asia/Riyadh")
    date_str = datetime.now(tz).strftime("%Y-%m-%d %H:%M")
    status = "🔓 مفتوح" if data["registration_open"] else "🔒 مغلق"

    def format_list(items):
        if not items: return "لا يوجد"
        return "\n".join([f"{i}- {name}" + (" ✅" if name in data["readers"] and items == data["registered"] else "") 
                          for i, name in enumerate(items, start=1)])

    text = (
        "السلام عليكم ورحمة الله وبركاته 🌿\n\n"
        f"📅 {date_str}\n\n"
        "خادم القرآن الرقمي 💫\n\n"
        f"التسجيل {status}\n\n"
        "قائمة تسجيل الأدوار 📝\n\n"
        "✍️ المسجلات:\n" + format_list(data["registered"]) + "\n\n"
        "⛔️ المعتذرات:\n" + format_list(list(data["excused"])) + "\n\n"
        "🎧 المستمعات:\n" + format_list(list(data["listeners"])) + "\n\n"
        "🚫 المحظورات:\n" + format_list(list(data["blocked"])) + "\n\n"
        "﴿ وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ۚ وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ ﴾"
    )
    return text

# =========================
# ADMIN CHECK
# =========================
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        return any(admin.user.id == update.effective_user.id for admin in admins)
    except:
        return False

# =========================
# BUTTONS
# =========================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = update.effective_chat.id
    data = get_data(chat_id)
    await query.answer()
    user_name = query.from_user.full_name

    if user_name in data["blocked"]:
        await query.answer("🚫 أنتِ محظورة", show_alert=True)
        return

    if query.data in ["reset", "toggle"]:
        if not await is_admin(update, context):
            await query.answer("🚫 للمشرفات فقط", show_alert=True)
            return
        if query.data == "reset":
            data["registered"].clear()
            data["readers"].clear()
            data["listeners"].clear()
            data["excused"].clear()
        elif query.data == "toggle":
            data["registration_open"] = not data["registration_open"]
        await query.edit_message_text(text=build_text(chat_id), reply_markup=menu())
        return

    if not data["registration_open"]:
        await query.answer("🔒 التسجيل مغلق", show_alert=True)
        return

    # منطق الأزرار
    if query.data == "register":
        if user_name not in data["registered"]: data["registered"].append(user_name)
        data["listeners"].discard(user_name)
        data["excused"].discard(user_name)
    elif query.data == "read":
        if user_name in data["registered"]: data["readers"].add(user_name)
    elif query.data == "listener":
        data["listeners"].add(user_name)
        if user_name in data["registered"]: data["registered"].remove(user_name)
        data["readers"].discard(user_name)
        data["excused"].discard(user_name)
    elif query.data == "excused":
        data["excused"].add(user_name)
        if user_name in data["registered"]: data["registered"].remove(user_name)
        data["readers"].discard(user_name)
        data["listeners"].discard(user_name)
    elif query.data == "remove":
        if user_name in data["registered"]: data["registered"].remove(user_name)
        data["readers"].discard(user_name)
        data["listeners"].discard(user_name)
        data["excused"].discard(user_name)

    await query.edit_message_text(text=build_text(chat_id), reply_markup=menu())

# (بقية الدوال: ban, unban, start, help يرجى تمرير chat_id لها بنفس الطريقة)
# مثال لتعديل ban:
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    data = get_data(chat_id)
    if not await is_admin(update, context): return
    if update.message.reply_to_message:
        user_name = update.message.reply_to_message.from_user.full_name
        data["blocked"].add(user_name)
        # ... مسح الاسم من القوائم الأخرى
        await update.message.reply_text(build_text(chat_id), reply_markup=menu())

# ... (أكمل باقي الدوال بنفس نمط تمرير chat_id)
