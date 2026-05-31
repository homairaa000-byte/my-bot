import os
from datetime import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN: raise Exception("BOT_TOKEN missing")

chat_data = {}

def get_data(chat_id):
    if chat_id not in chat_data:
        chat_data[chat_id] = {
            "registered": [], "readers": set(), "listeners": set(),
            "excused": set(), "blocked": set(), "registration_open": True
        }
    return chat_data[chat_id]

def menu():
    keyboard = [
        [InlineKeyboardButton("✅ قرأت", callback_data="read"), InlineKeyboardButton("✍️ سجل اسمي", callback_data="register")],
        [InlineKeyboardButton("🎧 مستمعة", callback_data="listener"), InlineKeyboardButton("⛔️ معتذرة", callback_data="excused")],
        [InlineKeyboardButton("🧹 تصفير", callback_data="reset"), InlineKeyboardButton("🔒 قفل/فتح", callback_data="toggle")],
        [InlineKeyboardButton("❌ حذف اسمي", callback_data="remove")]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_text(chat_id):
    data = get_data(chat_id)
    tz = pytz.timezone("Asia/Riyadh")
    date_str = datetime.now(tz).strftime("%Y-%m-%d %H:%M")
    status = "🔓 مفتوح" if data["registration_open"] else "🔒 مغلق"

    def format_list(items, is_registered=False):
        if not items: return "لا يوجد"
        return "\n".join([f"{i+1}- {name}{' ✅' if (is_registered and name in data['readers']) else ''}" 
                          for i, name in enumerate(items)])

    return (
        "السلام عليكم ورحمة الله وبركاته 🌿\n\n"
        f"📅 {date_str}\n\nخادم القرآن الرقمي 💫\n\n"
        f"التسجيل {status}\n\nقائمة تسجيل الأدوار 📝\n\n"
        f"✍️ المسجلات:\n{format_list(data['registered'], True)}\n\n"
        f"⛔️ المعتذرات:\n{format_list(list(data['excused']))}\n\n"
        f"🎧 المستمعات:\n{format_list(list(data['listeners']))}\n\n"
        f"🚫 المحظورات:\n{format_list(list(data['blocked']))}\n\n"
        "﴿ وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ۚ وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ ﴾"
    )

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        return any(admin.user.id == update.effective_user.id for admin in admins)
    except: return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        await update.message.reply_text("أهلاً بك في خادم القرآن الرقمي 💫\nاستخدم /help لمعرفة طريقة العمل.")
    else:
        await update.message.reply_text("أهلاً بك! استخدم /list لعرض القائمة أو /help للمساعدة.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💡 **طريقة عمل خادم القرآن الرقمي:**\n\n- سجل اسمك ثم اضغط '✅ قرأت' عند انتهائك.\n- الضغط المتكرر على 'قرأت' يبدل الحالة (تفعيل/إلغاء).\n- المشرفات فقط يتحكمن في 'تصفير' و 'قفل/فتح' القائمة.")

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(build_text(update.effective_chat.id), reply_markup=menu())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = update.effective_chat.id
    user_name = update.effective_user.full_name
    data = get_data(chat_id)
    await query.answer()

    if query.data == "read":
        if user_name not in data["registered"]:
            await query.answer("يجب تسجيل اسمك أولاً!", show_alert=True)
            return
        if user_name in data["readers"]: data["readers"].remove(user_name)
        else: data["readers"].add(user_name)
    elif query.data in ["reset", "toggle"]:
        if not await is_admin(update, context):
            await query.answer("للمشرفات فقط!", show_alert=True)
            return
        if query.data == "toggle": data["registration_open"] = not data["registration_open"]
        elif query.data == "reset":
            data["registered"] = []
            data["readers"] = set()
            data["excused"] = set()
    elif query.data == "register":
        if not data["registration_open"]:
            await query.answer("التسجيل مغلق حالياً.", show_alert=True)
            return
        if user_name not in data["registered"]: data["registered"].append(user_name)
    elif query.data == "listener": data["listeners"].add(user_name)
    elif query.data == "excused": data["excused"].add(user_name)
    elif query.data == "remove":
        if user_name in data["registered"]: data["registered"].remove(user_name)
        if user_name in data["readers"]: data["readers"].remove(user_name)
    await query.edit_message_text(build_text(chat_id), reply_markup=menu())

if __name__ == '__main__':
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CallbackQueryHandler(buttons))
    application.run_polling()
