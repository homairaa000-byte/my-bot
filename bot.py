import logging
import threading
from flask import Flask
from telegram.ext import ApplicationBuilder, MessageHandler, filters

# إعداد السجلات لمتابعة حالة البوت
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# التوكن الخاص بك
BOT_TOKEN = '8817548868:AAEBP-C8ift1Z-_ydpDzmticw18gDW2_Kjc'

# إعداد Flask لغرض البقاء نشطاً (UptimeRobot)
app = Flask(__name__)

@app.route('/')
def home():
    return "البوت يعمل الآن بنجاح!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# وظيفة البوت
async def handle_message(update, context):
    await update.message.reply_text("أهلاً! البوت يعمل الآن 24/7 على السحابة.")

if __name__ == '__main__':
    # تشغيل Flask في خيط منفصل (Thread) لضمان عدم حدوث تضارب
    threading.Thread(target=run_flask).start()

    # تشغيل البوت بطريقة polling
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("🚀 البوت بدأ العمل الآن!")
    application.run_polling()
