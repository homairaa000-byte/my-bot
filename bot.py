import os
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import asyncio

TOKEN = '8817548868:AAHA4NrB7j28k7xSoIe2EVd3nZjZoA_rHJY'
PORT = int(os.environ.get('PORT', 8080))
WEBHOOK_URL = 'https://my-bot-pwus.onrender.com'

app = Flask(__name__)
# إنشاء التطبيق بشكل صحيح للتعامل مع الـ Webhook
application = Application.builder().token(TOKEN).build()

# ... (بقية منطق الأزرار والأسماء كما في الكود السابق الذي اتفقنا عليه) ...

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    # استخدام asyncio.run_coroutine_threadsafe لإصلاح مشكلة الـ await
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run_coroutine_threadsafe(application.process_update(update), application.create_task_group())
    return 'ok'

if __name__ == '__main__':
    # تهيئة الويب هوك عند التشغيل
    asyncio.run(application.bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}"))
    app.run(host='0.0.0.0', port=PORT)
