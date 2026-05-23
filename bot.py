import os
import threading
from flask import Flask
from telegram.ext import ApplicationBuilder, MessageHandler, filters

BOT_TOKEN = '8817548868:AAHA4NrB7j28k7xSoIe2EVd3nZjZoA_rHJY'
PORT = int(os.environ.get("PORT", 8080))

app = Flask(__name__)

@app.route('/')
def home():
    return "البوت يعمل الآن!"

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

async def handle_message(update, context):
    await update.message.reply_text("البوت يعمل الآن بنجاح!")

if __name__ == '__main__':
    # تشغيل الخادم
    threading.Thread(target=run_flask).start()
    
    # تشغيل البوت
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.run_polling()
