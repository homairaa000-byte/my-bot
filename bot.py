import os
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

TOKEN = '8817548868:AAHA4NrB7j28k7xSoIe2EVd3nZjZoA_rHJY'
PORT = int(os.environ.get('PORT', 8080))
WEBHOOK_URL = 'https://my-bot-pwus.onrender.com' 

app = Flask(__name__)
bot = Bot(TOKEN)
application = Application.builder().token(TOKEN).build()

# بيانات البوت
students = {} 
banned = []

def get_list():
    readers = [f"✅ {name}" for name, s in students.items() if s == "قرأت"]
    listeners = [f"🎧 {name}" for name, s in students.items() if s == "مستمعة"]
    absents = [f"⛔ {name}" for name, s in students.items() if s == "معتذرة"]
    text = "📋 **قائمة الإسم الثلاثي للطالبات**\n\n✅ القارئات:\n" + ("\n".join(readers) or "لا يوجد")
    text += "\n\n🎧 المستمعات:\n" + ("\n".join(listeners) or "لا يوجد")
    text += "\n\n⛔ المعتذرات:\n" + ("\n".join(absents) or "لا يوجد")
    return text

async def start(update, context):
    keyboard = [
        [InlineKeyboardButton("✅ قرأت", callback_data='read'), InlineKeyboardButton("🎧 مستمعة", callback_data='listen')],
        [InlineKeyboardButton("⛔ معتذرة", callback_data='absent'), InlineKeyboardButton("❌ حذف اسمي", callback_data='remove')],
        [InlineKeyboardButton("🧹 تصفير القائمة", callback_data='reset')]
    ]
    await update.message.reply_text(get_list(), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def button(update, context):
    query = update.callback_query
    user = query.from_user.full_name
    if user in banned: await query.answer("ممنوع! أنتِ محظورة."); return
    
    if query.data == 'read': students[user] = "قرأت"
    elif query.data == 'listen': students[user] = "مستمعة"
    elif query.data == 'absent': students[user] = "معتذرة"
    elif query.data == 'remove': students.pop(user, None)
    elif query.data == 'reset': students.clear()
    
    await query.edit_message_text(text=get_list(), reply_markup=query.message.reply_markup, parse_mode='Markdown')
    await query.answer("تم التحديث!")

async def ban(update, context):
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user.full_name
        banned.append(target); students.pop(target, None)
        await update.message.reply_text(f"🚫 تم حظر {target}")

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button))
application.add_handler(MessageHandler(filters.Regex('^حظر$') & filters.REPLY, ban))

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    application.update_queue.put(Update.de_json(request.get_json(force=True), bot))
    return 'ok'

if __name__ == '__main__':
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    app.run(host='0.0.0.0', port=PORT)
