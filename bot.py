import logging
from telegram.ext import ApplicationBuilder, MessageHandler, filters

# إعداد السجلات
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ضعي التوكن الخاص بك هنا
BOT_TOKEN = '8817548868:AAHA4NrB7j28k7xSoIe2EVd3nZjZoA_rHJY'

# وظيفة البوت
async def handle_message(update, context):
    await update.message.reply_text("البوت يعمل الآن بنجاح!")

if __name__ == '__main__':
    print("🚀 البوت بدأ العمل!")
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    # استخدام Polling وهو الطريقة الصحيحة
    application.run_polling()
