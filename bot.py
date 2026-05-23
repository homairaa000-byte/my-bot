 import logging
from telegram.ext import ApplicationBuilder, MessageHandler, filters

# التوكن الخاص بك
BOT_TOKEN = '8817548868:AAHA4NrB7j28k7xSoIe2EVd3nZjZoA_rHJY'

# وظيفة الرد
async def handle_message(update, context):
    await update.message.reply_text("البوت يعمل الآن بنجاح!")

if __name__ == '__main__':
    # بناء التطبيق
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    # تشغيل البوت مباشرة (بدون Flask أو Threads معقدة)
    print("🚀 البوت يعمل الآن!")
    application.run_polling()
