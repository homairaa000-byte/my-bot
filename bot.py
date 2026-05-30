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

    def format_list(items, is_registered=False):
        if not items: return "لا يوجد"
        result = ""
        for i, name in enumerate(items, start=1):
            check = " ✅" if (is_registered and name in data["readers"]) else ""
            result += f"{i}- {name}{check}\n"
        return result

    text = (
        "السلام عليكم ورحمة الله وبركاته 🌿\n\n"
        f"📅 {date_str}\n\n"
        "خادم القرآن الرقمي 💫\n\n"
        f"التسجيل {status}\n\n"
        "قائمة تسجيل الأدوار 📝\n\n"
        "✍️ المسجلات:\n" + format_list(data["registered"], True) + "\n"
        "⛔️ المعتذرات:\n" + format_list(list(data["excused"])) + "\n"
        "🎧 المستمعات:\n" + format_list(list(data["listeners"])) + "\n"
        "🚫 المحظورات:\n" + format_list(list(data["blocked"])) + "\n"
        "﴿ وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ۚ وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ ﴾"
    )
    return text

# =========================
# UTILS
# =========================
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        return any(admin.user.id == update.effective_user.id for admin in admins)
    except: return False

# =========================
# HANDLERS
# =========================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = update.effective_chat.id
    data = get_data(chat_id)
    await query.answer()
    user_name
