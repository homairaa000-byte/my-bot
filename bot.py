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

# تعريف المتغيرات العامة في البداية
students = {"قرأت": [], "مستمعة": [], "معتذرة": []}
registration_open = True

def get_status():
    status_text = "🔒 التسجيل: " + ("مفتوح ✅" if registration_open else "مغلق ⛔") + "\n\n"
    status_text += "📋 **قائمة الطالبات:**\n\n✅ القارئات:\n" + ("\n".join(students["قرأت"]) or "لا يوجد")
    status_text += "\n\n🎧 المستمعات:\n" + ("\n".join(students["مستمعة"]) or "لا يوجد")
    status_text += "\n\n🚫 المعتذرات:\n" + ("\n".join(students["معتذرة"]) or "لا يوجد")
    return status_text

async def start(update, context):
    keyboard = [
        [InlineKeyboardButton("✅ قرأت", callback_data='read'), InlineKeyboardButton("🎧 مستمعة", callback_data='listen')],
        [InlineKeyboardButton("🚫 معتذرة", callback_data='excuse'), InlineKeyboardButton("❌ حذف اسمي", callback_data='remove')],
        [InlineKeyboardButton("🔒 قفل/فتح التسجيل", callback_data='toggle'), InlineKeyboardButton("🧹 تصفير القائمة", callback_data='clear')]
    ]
    await update.message.reply_text(get_status(), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def button(update, context):
    global registration_open # هذا السطر يحل مشكلة الخطأ
    query = update.callback_query
    user = query.from_user.full_name
    uid = query.from_user.id
    chat_id = query.message.chat_id
    
    member = await context.bot.get_chat_member(chat_id, uid)
    is_admin = member.status in ['administrator', 'creator']

    if query.data in ['read', 'listen', 'excuse']:
        if not registration_open and not is_admin:
            await query.answer("التسجيل مغلق حالياً!", show_alert=True)
            return
        for cat in students:
            if user in students[cat]: students[cat].remove(user)
        students["قرأت" if query.data == 'read' else "مستمعة" if query.data == 'listen' else "معتذرة"].append(user)
    
    elif query.data == 'toggle' and is_admin:
        registration_open = not registration_open
        await query.answer(f"تم {'فتح' if registration_open else 'قفل'} التسجيل")
    
    elif query.data == 'clear' and is_admin:
        for cat in students: students[cat] = []
        await query.answer("تم تصفير القائمة!")

    await query.edit_message_text(text=get_status(), reply_markup=query.message.reply_markup, parse_mode='Markdown')

async def block_links(update, context):
    member = await context.bot.get_chat_member(update.message.chat_id, update.message.from_user.id)
    if member.status not in ['administrator', 'creator']:
        await update.message.delete()
        await update.message.reply_text("⛔ ممنوع إرسال روابط هنا!", reply_to_message_id=update.message.message_id)

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button))
application.add_handler(MessageHandler(filters.Entity("url"), block_links))

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    application.update_queue.put(Update.de_json(request.get_json(force=True), bot))
    return 'ok'

if __name__ == '__main__':
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    app.run(host='0.0.0.0', port=PORT)
