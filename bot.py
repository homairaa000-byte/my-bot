import os
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

# القوائم البرمجية
users, registered, readers, listeners, excused, blocked = {}, set(), set(), set(), set(), set()

# دالة التحقق من المشرفات
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        admins = await context.bot.get_chat_administrators(chat_id)
        return any(admin.user.id == update.effective_user.id for admin in admins)
    except: return False

# دالة مراقبة الرسائل (الحظر + حذف الروابط)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    uid = update.message.from_user.id
    
    # 1. منع المحظورين
    if uid in blocked:
        try: await update.message.delete()
        except: pass
        return

    # 2. حذف الروابط مع تنبيه خاص
    url_pattern = r'(https?://\S+|www\.\S+|\.com|\.net|\.org)'
    if re.search(url_pattern, update.message.text):
        try:
            await update.message.delete()
            alert = await update.message.reply_text(
                "🚫🚫🚫 تنبيه ...\nارسال روابط من دون إذن المشرفات يعرضك للحذف أو الحظر"
            )
            # حذف التنبيه بعد 5 ثوانٍ
            context.job_queue.run_once(
                lambda ctx: ctx.bot.delete_message(chat_id=update.message.chat_id, message_id=alert.message_id), 
                5
            )
        except: pass

# دالة الترحيب والبدء
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == 'private':
        welcome_text = (
            "✨ أهلاً بكِ في بوت 'خادم القرآن الرقمي' ✨\n\n"
            "هذا البوت مخصص لمتابعة التسجيلات في المجموعة.\n\n"
            "📌 **كيفية عمل البوت:**\n"
            "1. أضيفي البوت للمجموعة واجعليه 'مشرفاً' (لتمكينه من الحذف والحظر).\n"
            "2. استخدمي الأزرار في المجموعة لتسجيل اسمكِ.\n"
            "3. البوت يحذف الروابط تلقائياً ويمنع المحظورين.\n"
        )
        await update.message.reply_text(welcome_text)
    else:
        # هنا يتم عرض قائمة الأزرار (تأكدي من وجود دالة build_text و menu لديكِ)
        await update.message.reply_text("مرحباً بكِ في خادم القرآن الرقمي، استعملي الأزرار أدناه:")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    
    # إضافة المراقب للرسائل (يعمل على كل نص ليس أمراً)
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons)) # تأكدي من وجود دالة buttons
    
    print("البوت يعمل الآن...")
    app.run_polling(drop_pending_updates=True)
