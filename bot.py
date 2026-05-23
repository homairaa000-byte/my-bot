import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# التوكن الخاص بك
BOT_TOKEN = '8817548868:AAHA4NrB7j28k7xSoIe2EVd3nZjZoA_rHJY'
PORT = int(os.environ.get("PORT", 8080))

app = Flask(__name__)

# خادم الويب (ليظل السيرفر نشطاً)
@app.route('/')
def home():
    return "البوت يعمل الآن!"

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

# أوامر البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك! أنا البوت الخاص بك. كيف يمكنني مساعدتك اليوم؟")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("الأوامر المتاحة:\n/start - بدء البوت\n/help - المساعدة")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("وصلتني رسالتك! البوت يعمل بنجاح.")

if __name__ == '__main__':
    # 1. تشغيل الخادم في الخلفية
    threading.Thread(target=run_flask).start()
    
    # 2. إعداد البوت
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # ربط الأوامر
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    # 3. تشغيل البوت
    application.run_polling()
