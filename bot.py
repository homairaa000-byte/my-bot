import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

BOT_TOKEN = '8817548868:AAHA4NrB7j28k7xSoIe2EVd3nZjZoA_rHJY'
PORT = int(os.environ.get("PORT", 8080))

app = Flask(__name__)
bot = Bot(BOT_TOKEN)

# إعداد البوت
application = ApplicationBuilder().token(BOT_TOKEN).build()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("البوت يعمل بنجاح!")

application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    # معالجة رسائل تليجرام الواردة
    return "ok", 200

@app.route('/')
def home():
    return "البوت يعمل!"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=PORT)
