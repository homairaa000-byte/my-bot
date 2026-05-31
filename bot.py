import os
import logging
from datetime import datetime
import pytz
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, filters

# إعداد السيرفر
app = Flask(__name__)
@app.route('/')
def index(): return "Bot is running!"
def run(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

logging.basicConfig(level=logging.INFO)
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
    tz = pytz.timezone("Africa/Tripoli")
    date_str = datetime.now(tz).strftime("%Y-%m-%d %H:%M")
    status = "🔓 مفتوح" if data["registration_open"] else "🔒 مغلق"

    def format_list(items, is_registered=False):
        if not items: return "لا يوجد"
        return "\n".join([f"{i+1}- {name}{' ✅' if (is_registered and name in data['readers']) else ''}" 
                          for i, name in enumerate(items) if name not in data["blocked"]])

    return (
        "السلام عليكم ورحمة الله وبركاته 🌿\n\n"
        f"📅 {date_str}\n\nخادم القرآن الرقمي 💫\n\n"
        f"التسجيل {status}\n\nقائمة تسجيل الأدوار 📝\n\n"
        f"✍️ المسجلات:\n{format_list(data['registered'], True)}\n\n"
        f"⛔️ المعتذرات:\n{format_list(list(data['excused']))}\n\n"
        f"🎧 المستمعات:\n{format_list(list(data['listeners']))}\n\n"
        "﴿ وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ۚ وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ ﴾"
    )

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        return any(admin.user.id == update.effective_user.id for admin in admins)
    except: return False

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    if update.message.reply_to_message:
        user_to_ban = update.message.reply_to_message.from_user.full_name
        data = get_data(update.effective_chat.id)
        data["blocked"].add(user_to_ban)
        if user_to_ban in data["registered"]: data["registered"].remove(user_to_ban)
        await update.message.reply_text(f"🚫 تم حظر العضوة: {user_to_ban}")
    else:
        await update.message.reply_text("يرجى الرد على رسالة العضوة المراد حظرها.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك في خادم القرآن الرقمي 💫\nاستخدم /help للمساعدة.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "💡 **دليل استخدام خادم القرآن الرقمي:**\n\n"
        "✍️ **سجل اسمي:** لإضافة اسمك إلى قائمة المسجلات.\n"
        "✅ **قرأت:** لتأكيد قراءتك (يجب أن تكوني مسجلة أولاً).\n"
        "🎧 **مستمعة:** لنقل اسمك إلى قائمة المستمعات.\n"
        "⛔️ **معتذرة:** لنقل اسمك إلى قائمة المعتذرات.\n"
        "❌ **حذف اسمي:** لإزالة اسمك تماماً من أي قائمة.\n\n"
        "🔒 **للمشرفات فقط:**\n"
        "- 🧹 **تصفير:** لمسح جميع القوائم.\n"
        "- 🔒 **قفل/فتح:** للتحكم في قبول مسجلات جدد.\n"
        "- 🚫 **حظر عضوة:** ردي على رسالة العضوة بالأمر /ban لحظرها."
    )
    await update.message.reply_text(help_text)

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(build_text(update.effective_chat.id), reply_markup=menu())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = update.effective_chat.id
    user_name = update.effective_user.full_name
    data = get_data(chat_id)
    
    if user_name in data["blocked"]:
        await query.answer("أنتِ محظورة من استخدام البوت!", show_alert=True)
        return
    await query.answer()

    def remove_user_everywhere(name):
        if name in data["registered"]: data["registered"].remove(name)
        if name in data["readers"]: data["readers"].remove(name)
        if name in data["listeners"]: data["listeners"].remove(name)
        if name in data["excused"]: data["excused"].remove(name)

    if query.data == "read":
        if user_name not in data["registered"]:
            await query.answer("يجب تسجيل اسمك أولاً!", show_alert=True)
            return
        if user_name in data["readers"]: data["readers"].remove(user_name)
        else: data["readers"].add(user_name)
    elif query.data == "register":
        if not data["registration_open"]:
            await query.answer("التسجيل مغلق حالياً.", show_alert=True)
            return
        remove_user_everywhere(user_name)
        data["registered"].append(user_name)
    elif query.data == "listener":
        remove_user_everywhere(user_name)
        data["listeners"].add(user_name)
    elif query.data == "excused":
        remove_user_everywhere(user_name)
        data["excused"].add(user_name)
    elif query.data == "remove":
        remove_user_everywhere(user_name)
    elif query.data in ["reset", "toggle"]:
        if not await is_admin(update, context):
            await query.answer("للمشرفات فقط!", show_alert=True)
            return
        if query.data == "toggle": data["registration_open"] = not data["registration_open"]
        elif query.data == "reset":
            data["registered"] = []; data["readers"] = set(); data["excused"] = set(); data["listeners"] = set()
            
    await query.edit_message_text(build_text(chat_id), reply_markup=menu())

if __name__ == '__main__':
    Thread(target=run).start()
    application = Application.builder().token(TOKEN).build()
    
    # ربط الأوامر
    application.add_handler(CommandHandler("start", start, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CallbackQueryHandler(buttons))
    application.run_polling()
