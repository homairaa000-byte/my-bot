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

# تعريف القوائم والمتغير العام
registration_open = True
students = {"قرأت": [], "مستمعة": [], "معتذرة": []}

def get_status_text():
    status = "مفتوح ✅" if registration_open else "مغلق ⛔"
    text = f"🔒 حالة التسجيل: {status}\n\n📋 القائمة:\n"
    for category, names in students.items():
        text += f"\n{category}:\n" + ("\n".join(names) if names else "لا يوجد")
    return text

async def start(update, context):
    keyboard = [
        [InlineKeyboardButton("✅ قرأت", callback_data='read'), InlineKeyboardButton("🎧 مستمعة", callback_data='listen')],
        [InlineKeyboardButton("🚫 معتذرة", callback_data='excuse')],
        [InlineKeyboardButton("❌ حذف اسمي", callback_data='remove')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(get_status_text(), reply_markup=reply_markup)

async def button_click(update, context):
    global registration_open
    query = update.callback_query
    user = query.from_user.full_name
    data = query.data

    if not registration_open and data != 'remove':
        await query.answer("التسجيل مغلق حالياً!", show_alert=True)
        return

    # منطق إضافة أو حذف الأسماء هنا...
    await query.answer(f"تم اختيار: {data}")

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button_click))

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    application.update_queue.put(Update.de_json(request.get_json(force=True), bot))
    return 'ok'

if __name__ == '__main__':
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    app.run(host='0.0.0.0', port=PORT)
