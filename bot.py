import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

# القوائم والبيانات
registered, readers, listeners, excused, blocked = set(), set(), set(), set(), set()

# --- الدوال المساعدة ---

def menu():
    keyboard = [
        [InlineKeyboardButton("✅ سجل اسمي", callback_data="register"), InlineKeyboardButton("🎧 مستمعة", callback_data="listener")],
        [InlineKeyboardButton("🚫 معتذرة", callback_data="excused"), InlineKeyboardButton("🧹 تصفير", callback_data="reset")],
        [InlineKeyboardButton("🔒 قفل/فتح", callback_data="toggle")]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_text():
    return (f"✨ خادم القرآن الرقمي ✨\n\n"
            f"👤 المسجلات: {len(registered)}\n"
            f"🎧 المستمعات: {len(listeners)}\n"
            f"🚫 المعتذرات: {len(excused)}")

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        admins = await context.bot.get_chat_administrators(chat_id)
        return any(admin.user.id == update.effective_user.id for admin in admins)
    except: return False

# --- الأوامر والدوال ---

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    
    help_text = (
        "📖 **دليل المشرفات - خادم القرآن الرقمي**\n\n"
        "🔹 `/list` - عرض قائمة المسجلات والمستمعات.\n"
        "🔹 `/help` - عرض قائمة التعليمات.\n\n"
        "📌 **خطوات العمل للمشرفات:**\n"
        "1. تأكدي من منح البوت صلاحية (حذف الرسائل).\n"
        "2. تأكدي من إيقاف (Privacy Mode) عبر @BotFather.\n"
        "3. استخدمي الأزرار للتحكم في التسجيل.\n"
        "4. أي روابط تُرسل دون إذن سيتم حذفها تلقائياً.\n\n"
        "اللهم اجعل أعمالنا خالصة لوجهك الكريم."
    )
    try: await update.message.delete()
    except: pass
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def show_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.delete()
    except: pass
    await update.message.reply_text(build_text(), reply_markup=menu())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    uid = update.message.from_user.id
    
    if uid in blocked:
        try: await update.message.delete()
        except: pass
        return

    if update.message.parse_entities(types=['url']):
        try:
            await update.message.delete()
            alert = await update.message.reply_text("🚫🚫🚫 تنبيه ...\nارسال روابط من دون إذن المشرفات يعرضك للحذف أو الحظر")
            context.job_queue.run_once(lambda ctx: ctx.bot.delete_message(chat_id=update.message.chat_id, message_id=alert.message_id), 5)
        except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == 'private':
        welcome_text = (
            "✨ أهلاً بكِ في 'خادم القرآن الرقمي' ✨\n\n"
            "📌 **خطوات عمل البوت:**\n"
            "1. أضيفي البوت لمجموعتكِ واجعليه مشرفاً.\n"
            "2. استخدمي `/help` في المجموعة (للمشرفات فقط) لمعرفة الأوامر.\n"
            "3. البوت يحذف الروابط الممنوعة ويمنع المحظورين.\n\n"
            "اللهم اجعل أعمالنا خالصة لوجهك الكريم."
        )
        await update.message.reply_text(welcome_text)
    else:
        await update.message.reply_text(build_text(), reply_markup=menu())

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("list", show_list))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("البوت يعمل الآن...")
    app.run_polling(drop_pending_updates=True)
