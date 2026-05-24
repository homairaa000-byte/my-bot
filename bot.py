import os
import asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# =========================
# إعدادات البوت
# =========================

TOKEN = '8817548868:AAHA4NrB7j28k7xSoIe2EVd3nZjZoA_rHJY'

PORT = int(os.environ.get('PORT', 10000))

WEBHOOK_URL = 'https://my-bot-pwus.onrender.com'

app = Flask(__name__)

application = Application.builder().token(TOKEN).build()

# =========================
# بيانات الطالبات
# =========================

students = {
    "قرأت": [],
    "مستمعة": [],
    "معتذرة": []
}

registration_open = True

# =========================
# عرض القائمة
# =========================

def get_status():

    status = "مفتوح ✅" if registration_open else "مغلق ⛔"

    text = f"🔒 التسجيل: {status}\n\n"
    text += "📋 قائمة الطالبات:\n"

    for cat, names in students.items():

        text += f"\n\n{cat}:\n"

        if names:
            text += "\n".join(names)
        else:
            text += "لا يوجد"

    return text

# =========================
# حذف الاسم
# =========================

def remove_name(name):

    for category in students.values():

        if name in category:
            category.remove(name)

# =========================
# أمر start
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [

        [
            InlineKeyboardButton(
                "✅ قرأت",
                callback_data='read'
            ),

            InlineKeyboardButton(
                "🎧 مستمعة",
                callback_data='listen'
            )
        ],

        [
            InlineKeyboardButton(
                "🚫 معتذرة",
                callback_data='excuse'
            ),

            InlineKeyboardButton(
                "❌ حذف اسمي",
                callback_data='remove'
            )
        ],

        [
            InlineKeyboardButton(
                "🔒 قفل/فتح التسجيل",
                callback_data='toggle'
            )
        ],

        [
            InlineKeyboardButton(
                "🧹 تصفير القائمة",
                callback_data='clear'
            )
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        get_status(),
        reply_markup=reply_markup
    )

# =========================
# معالجة الأزرار
# =========================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global registration_open

    query = update.callback_query

    await query.answer()

    user = query.from_user.first_name

    data = query.data

    # حذف الاسم من جميع القوائم
    remove_name(user)

    if data == 'read':

        if registration_open:
            students["قرأت"].append(user)

    elif data == 'listen':

        if registration_open:
            students["مستمعة"].append(user)

    elif data == 'excuse':

        if registration_open:
            students["معتذرة"].append(user)

    elif data == 'remove':

        pass

    elif data == 'toggle':

        registration_open = not registration_open

    elif data == 'clear':

        students["قرأت"].clear()
        students["مستمعة"].clear()
        students["معتذرة"].clear()

    keyboard = [

        [
            InlineKeyboardButton(
                "✅ قرأت",
                callback_data='read'
            ),

            InlineKeyboardButton(
                "🎧 مستمعة",
                callback_data='listen'
            )
        ],

        [
            InlineKeyboardButton(
                "🚫 معتذرة",
                callback_data='excuse'
            ),

            InlineKeyboardButton(
                "❌ حذف اسمي",
                callback_data='remove'
            )
        ],

        [
            InlineKeyboardButton(
                "🔒 قفل/فتح التسجيل",
                callback_data='toggle'
            )
        ],

        [
            InlineKeyboardButton(
                "🧹 تصفير القائمة",
                callback_data='clear'
            )
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=get_status(),
        reply_markup=reply_markup
    )

# =========================
# الصفحة الرئيسية
# =========================

@app.route('/')
def home():

    return "Bot is running!"

# =========================
# Webhook
# =========================

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():

    update = Update.de_json(
        request.get_json(force=True),
        application.bot
    )

    asyncio.run(
        application.process_update(update)
    )

    return 'ok', 200

# =========================
# تشغيل البوت
# =========================

async def setup():

    await application.initialize()

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CallbackQueryHandler(buttons)
    )

    await application.bot.set_webhook(
        url=f"{WEBHOOK_URL}/{TOKEN}"
    )

if __name__ == '__main__':

    loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)

    loop.run_until_complete(setup())

    app.run(
        host='0.0.0.0',
        port=PORT
    )
