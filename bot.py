import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

TOKEN = '8817548868:AAHA4NrB7j28k7xSoIe2EVd3nZjZoA_rHJY'
PORT = int(os.environ.get('PORT', 8080))
WEBHOOK_URL = 'https://my-bot-pwus.onrender.com'

app = Flask(__name__)
# بناء التطبيق بدون انتظار (بدون loop داخل الـ global scope)
application = Application.builder().token(TOKEN).build()

# هنا يمكنك إضافة دوال (start, button, block_links) كما هي في كودك السابق تماماً

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    # معالجة فورية وآمنة للرسائل الواردة
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run(application.process_update(update))
    return 'ok', 200

if __name__ == '__main__':
    # إعداد الويب هوك وتشغيل Flask
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(application.bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}"))
    app.run(host='0.0.0.0', port=PORT)
