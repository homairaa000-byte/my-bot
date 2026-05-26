import os
import datetime
import pytz
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

TOKEN = os.getenv("BOT_TOKEN")

# ... (بقية تعريفاتك كما هي) ...

if __name__ == '__main__':
    # التأكد من التوكين قبل التشغيل
    if not TOKEN:
        print("خطأ: لم يتم العثور على BOT_TOKEN في المتغيرات!")
    else:
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(buttons))
        print("البوت يعمل الآن...")
        app.run_polling(drop_pending_updates=True)
