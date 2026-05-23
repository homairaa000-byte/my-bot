import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler

TOKEN = '8817548868:AAHA4NrB7j28k7xSoIe2EVd3nZjZoA_rHJY'
# Render يعطي البوت منفذاً خاصاً، يجب أن نستخدمه
PORT = int(os.environ.get('PORT', 8080))
WEBHOOK_URL = 'https://my-bot-pwus.onrender.com' 

app = Flask(__name__)
bot = Bot(TOKEN)
application = Application.builder().token(TOKEN).build()

async def start(update, context):
    await update.message.reply_text("مرحباً! البوت يعمل الآن بنجاح.")

application.add_handler(CommandHandler("start", start))

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    application.update_queue.put(Update.de_json(request.get_json(force=True), bot))
    return 'ok'

if __name__ == '__main__':
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    # تشغيل التطبيق على المنفذ الصحيح
    app.run(host='0.0.0.0', port=PORT)
