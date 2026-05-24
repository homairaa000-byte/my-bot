import os
import asyncio
from datetime import datetime
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = '8817548868:AAHA4NrB7j28k7xSoIe2EVd3nZjZoA_rHJY'
PORT = int(os.environ.get('PORT', 10000))
WEBHOOK_URL = 'https://my-bot-pwus.onrender.com'

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

students = {"قرأت": [], "مستمعة": [], "معتذرة": [], "محظورات": []}
registration_open = True

# التحقق من أن المستخدم مشرف
async def is_admin(update, context):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    member = await context.bot.get_chat_member(chat_id, user_id)
    return member.status in ['administrator', 'creator']

def get_status():
    date_now = datetime.now().strftime("%Y / %m / %d")
    status = "مفتوح ✅" if registration_open else "مغلق ⛔"
    text = f"السلام عليكم ورحمة الله وبركاته\n\n"
    text += f"🤖 مساعد الأكاديمية\n📅 التاريخ: {date_now}\n"
    text += f"---------------------------\n"
    text += f"🔒 حالة التسجيل: {status}\n"
    
    for cat, names in students.items():
        text += f"\n{cat}:\n" + ("\n".join([f"• {n}" for n in names]) if names else "لا يوجد")
    
    text += f"\n---------------------------\n"
    text += "خذ الكتاب بقوة، واجعله من أولويات يومك، واقرأ تفسيره واعمل به، وأنت الرابح."
    return text

async def start(update, context):
    keyboard = [
        [InlineKeyboardButton("✅ قرأت", callback_data='read'), InlineKeyboardButton("🎧 مستمعة", callback_data='listen')],
        [InlineKeyboardButton("🚫 معتذرة", callback_data='excuse'), InlineKeyboardButton("❌ حذف اسمي", callback_data='remove')],
        [InlineKeyboardButton("🔒 قفل/فتح", callback_data='toggle'), InlineKeyboardButton("🧹 تصفير", callback_data='clear')],
        [InlineKeyboardButton("🚫 حظر طالبة", callback_data='ban')]
    ]
    await update.message.reply_text(get_status(), reply_markup=InlineKeyboardMarkup(keyboard))

async def buttons(update, context):
    query = update.callback_query
    await query.answer()
    user = query.from_user.full_name
    data = query.data
    
    # حظر المستخدم من النظام
    if user in students["محظورات"]:
        await query.answer("أنتِ محظورة من النظام!", show_alert=True)
        return

    if data in ['read', 'listen', 'excuse']:
        if registration_open:
            for cat in students:
                if user in students[cat]: students[cat].remove(user)
            students["قرأت" if data=='read' else "مستمعة" if data=='listen' else "معتذرة"].append(user)
    
    elif data == 'remove':
        for cat in students:
            if user in students[cat]: students[cat].remove(user)
            
    elif data in ['toggle', 'clear', 'ban']:
        if await is_admin(update, context):
            if data == 'toggle': global registration_open; registration_open = not registration_open
            elif data == 'clear': 
                for cat in students: 
                    if cat != "محظورات": students[cat] = []
            elif data == 'ban':
                await query.message.reply_text("للِحظر، ردي بكلمة 'حظر' على رسالة الطالبة المعنية.")
        else:
            await query.answer("للمشرفات فقط!", show_alert=True)

    await query.edit_message_text(text=get_status(), reply_markup=query.message.reply_markup)

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run(application.process_update(update))
    return 'ok', 200

# تشغيل البوت
if __name__ == '__main__':
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(buttons))
    asyncio.run(application.bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}"))
    app.run(host='0.0.0.0', port=PORT)
