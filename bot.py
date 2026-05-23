import os
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, CommandHandler, filters, ContextTypes

# النظام للعمل 24/7
app_flask = Flask('')
@app_flask.route('/')
def home(): return "البوت يعمل بنجاح!"
def run_flask(): app_flask.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
Thread(target=run_flask).start()

BOT_TOKEN = "8817548868:AAHA4NrB7j28k7xSoIe2EVd3nZjZoA_rHJY"

# القائمة (اللوحة)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("لوحة المشرفات 👮‍♀️", callback_data='admin')],
        [InlineKeyboardButton("المساعدة ℹ️", callback_data='help')],
        [InlineKeyboardButton("الإعدادات ⚙️", callback_data='settings')]
    ]
    await update.message.reply_text("أهلاً بكِ! أنا بوت الحماية، اختر من القائمة:", reply_markup=InlineKeyboardMarkup(keyboard))

# تنفيذ الأوامر المربوطة بالأزرار
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'admin':
        await query.edit_message_text("هنا لوحة التحكم الخاصة بالمشرفات.")
    elif query.data == 'help':
        await query.edit_message_text("هذا البوت يقوم بحذف الروابط تلقائياً.")
    elif query.data == 'settings':
        await query.edit_message_text("لا توجد إعدادات إضافية حالياً.")

# الحماية من الروابط
async def filter_group_links(update, context):
    message = update.effective_message
    if message and any(entity.type in ['url', 'text_link'] for entity in (message.entities or [])):
        await message.delete()
        await context.bot.send_message(message.chat_id, "⚠️ تم حذف رابط لأن الروابط ممنوعة!")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start)) # يربط الأمر بالدالة
    app.add_handler(CommandHandler("admin", start))
    app.add_handler(CommandHandler("settings", start))
    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.Entity("url"), filter_group_links))
    app.run_polling()

if __name__ == '__main__':
    main()
