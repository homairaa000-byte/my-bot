import logging
import os
from flask import Flask
from threading import Thread
from telegram.ext import ApplicationBuilder, MessageHandler, filters

# إعداد السجلات
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

BOT_TOKEN = '8817548868:AAHA4NrB7j28k7xSoIe2EVd3nZjZoA_rHJY'

# إنشاء خادم ويب بسيط لـ Render
app = Flask(__name__)

@app.route('/')
def home():
    return "البوت يعمل!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# وظيفة البوت
async def handle_message(update, context):
    await update.message.reply_text("البوت يعمل الآن بنجاح!")

if __name__ == '__main__':
    # تشغيل خادم الويب في الخلفية
    Thread(target=run_web_server).start()
    
    # تشغيل البوت
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("🚀 البوت بدأ العمل!")
    application.run_polling()
