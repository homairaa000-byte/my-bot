import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

# القوائم (Sets)
registered, readers, listeners, excused, blocked = set(), set(), set(), set(), set()
registration_open = True

# --- الدوال ---

def menu():
    # الترتيب حسب صورتك الأخيرة مع إضافة زر حذف الاسم
    keyboard = [
        [InlineKeyboardButton("✅ قرأت", callback_data="read"), InlineKeyboardButton("✍️ سجل اسمي", callback_data="register")],
        [InlineKeyboardButton("🎧 مستمعة", callback_data="listener"), InlineKeyboardButton("⛔️ معتذرة", callback_data="excused")],
        [InlineKeyboardButton("🧹 تصفير", callback_data="reset"), InlineKeyboardButton("🔒 قفل/فتح", callback_data="toggle")],
        [InlineKeyboardButton("❌ حذف اسمي", callback_data="remove")]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_text():
    status = "مفتوح 🔓" if registration_open else "مغلق 🔒"
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    text = (
        f"📅 {date_str}\n\n"
        f"🔒 التسجيل {status}\n\n"
        f"✍️ المسجلات:\n" + ("\n".join(registered) if registered else "لا يوجد") + "\n\n"
        f"✅ قرأت:\n" + ("\n".join(readers) if readers else "لا يوجد") + "\n\n"
        f"🎧 المستمعات:\n" + ("\n".join(listeners) if listeners else "لا يوجد") + "\n\n"
        f"⛔️ المعتذرات:\n" + ("\n".join(excused) if excused else "لا يوجد") + "\n\n"
        f"🚫 المحظورات:\n" + ("\n".join(blocked) if blocked else "لا يوجد") + "\n\n"
        f"{'{ وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا }'}"
    )
    return text

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        return any(admin.user.id == update.effective_user.id for admin in admins)
    except: return False

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # حماية الأوامر الإدارية
    if query.data in ["reset", "toggle"] and not await is_admin(update, context):
        await query.answer("🚫 للمشرفات فقط!", show_alert=True)
        return

    user_name = query.from_user.full_name
    
    # العمليات
    if query.data == "register": registered.add(user_name)
    elif query.data == "read": readers.add(user_name)
    elif query.data == "listener": listeners.add(user_name)
    elif query.data == "excused": excused.add(user_name)
    elif query.data == "remove":
        registered.discard(user_name); readers.discard(user_name)
        listeners.discard(user_name); excused.discard(user_name)
    elif query.data == "reset":
        registered.clear(); readers.clear(); listeners.clear(); excused.clear()
    elif query.data == "toggle":
        global registration_open
        registration_open = not registration_open
    
    await query.edit_message_text(text=build_text(), reply_markup=menu())

# --- الأوامر ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(build_text(), reply_markup=menu())

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    print("البوت يعمل الآن ومطابق للتنسيق المطلوب...")
    app.run_polling()
