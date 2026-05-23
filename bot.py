import os
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

TOKEN = '8817548868:AAHA4NrB7j28k7xSoIe2EVd3nZjZoA_rHJY'
PORT = int(os.environ.get('PORT', 8080))
WEBHOOK_URL = 'https://my-bot-pwus.onrender.com' 

app = Flask(__name__)
bot = Bot(TOKEN)
application = Application.builder().token(TOKEN).build()

# بيانات القائمة
students = {}

def get_list():
    text = "📋 **قائمة الطالبات:**\n\n"
    # ترتيب القائمة
    for name, status in students.items():
        text += f"- {name} ({status})\n"
    return text if students else "القائمة فارغة."

async def start(update, context):
    keyboard = [
        [InlineKeyboardButton("✅ قرأت", callback_data='read'), InlineKeyboardButton("🎧 مستمعة", callback_data='listen')]
    ]
    await update.message.reply_text("مرحباً بكِ في الأكاديمية! اختاري حالتك:", 
                                    reply_markup=InlineKeyboardMarkup(keyboard))

async def button(update, context):
    query = update.callback_query
    user = query.from_user.full_name
    students[user] = "قرأت" if query.data == 'read' else "مستمعة"
    await query.edit_message_text(text=get_list(), reply_markup=query.message.reply_markup)
    await query.answer("تم تسجيلك!")

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button))

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    application.update_queue.put(Update.de_json(request.get_json(force=True), bot))
    return 'ok'

if __name__ == '__main__':
    # تأكدي أن هذا السطر هو الذي يشغل السيرفر
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    app.run(host='0.0.0.0', port=PORT)
