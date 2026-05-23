import os
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = '8817548868:AAHA4NrB7j28k7xSoIe2EVd3nZjZoA_rHJY'
PORT = int(os.environ.get('PORT', 8080))
WEBHOOK_URL = 'https://my-bot-pwus.onrender.com' 

app = Flask(__name__)
bot = Bot(TOKEN)
application = Application.builder().token(TOKEN).build()

# قاموس لتخزين الحالات: {name: status}
students = {}

def get_list_text():
    # تقسيم الأسماء حسب الحالة
    readers = [f"✅ {name}" for name, status in students.items() if status == "قرأت"]
    listeners = [name for name, status in students.items() if status == "مستمعة"]
    absents = [name for name, status in students.items() if status == "معتذرة"]
    
    text = "📋 **قائمة الطالبات:**\n\n"
    text += "✅ **القارئات:**\n" + ("\n".join(readers) if readers else "لا يوجد") + "\n\n"
    text += "🎧 **المستمعات:**\n" + ("\n".join(listeners) if listeners else "لا يوجد") + "\n\n"
    text += "⛔ **المعتذرات:**\n" + ("\n".join(absents) if absents else "لا يوجد")
    return text

async def start(update, context):
    user = update.effective_user.full_name
    if user not in students:
        students[user] = "مسجلة"
    
    keyboard = [
        [InlineKeyboardButton("✅ قرأت", callback_data='read'), InlineKeyboardButton("🎧 مستمعة", callback_data='listen')],
        [InlineKeyboardButton("⛔ معتذرة", callback_data='absent')]
    ]
    await update.message.reply_text(get_list_text(), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def button(update, context):
    query = update.callback_query
    user = query.from_user.full_name
    if query.data == 'read': students[user] = "قرأت"
    elif query.data == 'listen': students[user] = "مستمعة"
    elif query.data == 'absent': students[user] = "معتذرة"
    
    await query.edit_message_text(text=get_list_text(), reply_markup=query.message.reply_markup, parse_mode='Markdown')
    await query.answer("تم تحديث حالتك!")

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button))

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    application.update_queue.put(update)
    return 'ok'

if __name__ == '__main__':
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    app.run(host='0.0.0.0', port=PORT)
