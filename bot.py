import os
from datetime import datetime
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
)
import asyncio

TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)

application = Application.builder().token(TOKEN).build()

students = {
    "قرأت": [],
    "مستمعة": [],
    "معتذرة": [],
    "محظورات": []
}

registration_open = True


# التحقق من المشرفة
async def is_admin(update, context):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    member = await context.bot.get_chat_member(chat_id, user_id)

    return member.status in ["administrator", "creator"]


# إنشاء الرسالة
def get_status():
    date_now = datetime.now().strftime("%Y / %m / %d")

    status = "مفتوح ✅" if registration_open else "مغلق ⛔"

    text = (
        "السلام عليكم ورحمة الله وبركاته\n\n"
        "🤖 مساعد الأكاديمية\n"
        f"📅 التاريخ: {date_now}\n"
        "---------------------------\n"
        f"🔒 حالة التسجيل: {status}\n"
    )

    for cat, names in students.items():
        text += f"\n{cat}:\n"

        if names:
            text += "\n".join([f"• {n}" for n in names])
        else:
            text += "لا يوجد"

    text += (
        "\n---------------------------\n"
        "خذ الكتاب بقوة، واجعله من أولويات يومك، "
        "واقرأ تفسيره واعمل به، وأنت الرابح."
    )

    return text


# أمر start
async def start(update, context):
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ قرأت",
                callback_data="read"
            ),

            InlineKeyboardButton(
                "🎧 مستمعة",
                callback_data="listen"
            )
        ],

        [
            InlineKeyboardButton(
                "🚫 معتذرة",
                callback_data="excuse"
            ),

            InlineKeyboardButton(
                "❌ حذف اسمي",
                callback_data="remove"
            )
        ],

        [
            InlineKeyboardButton(
                "🔒 قفل/فتح",
                callback_data="toggle"
            ),

            InlineKeyboardButton(
                "🧹 تصفير",
                callback_data="clear"
            )
        ],

        [
            InlineKeyboardButton(
                "🚫 حظر طالبة",
                callback_data="ban"
            )
        ]
    ]

    await update.message.reply_text(
        get_status(),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# الأزرار
async def buttons(update, context):
    global registration_open

    query = update.callback_query

    await query.answer()

    user = query.from_user.full_name

    data = query.data

    # تحقق الحظر
    if user in students["محظورات"]:
        await query.answer(
            "أنتِ محظورة من النظام!",
            show_alert=True
        )
        return

    # تسجيل
    if data in ["read", "listen", "excuse"]:

        if registration_open:

            for cat in students:
                if user in students[cat]:
                    students[cat].remove(user)

            if data == "read":
                students["قرأت"].append(user)

            elif data == "listen":
                students["مستمعة"].append(user)

            elif data == "excuse":
                students["معتذرة"].append(user)

    # حذف الاسم
    elif data == "remove":

        for cat in students:
            if user in students[cat]:
                students[cat].remove(user)

    # أوامر المشرفة
    elif data in ["toggle", "clear", "ban"]:

        if await is_admin(update, context):

            if data == "toggle":
                registration_open = not registration_open

            elif data == "clear":

                for cat in students:
                    if cat != "محظورات":
                        students[cat] = []

            elif data == "ban":

                await query.message.reply_text(
                    "للِحظر، ردي بكلمة 'حظر' "
                    "على رسالة الطالبة."
                )

        else:
            await query.answer(
                "للمشرفات فقط!",
                show_alert=True
            )

    await query.edit_message_text(
        text=get_status(),
        reply_markup=query.message.reply_markup
    )


# webhook
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(
        request.get_json(force=True),
        application.bot
    )

    asyncio.run(application.process_update(update))

    return "ok"


# الصفحة الرئيسية
@app.route("/")
def home():
    return "Bot is running!"


async def setup():
    await application.initialize()
    await application.bot.set_webhook(
        url=f"{WEBHOOK_URL}/{TOKEN}"
    )


if __name__ == "__main__":

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CallbackQueryHandler(buttons)
    )

    asyncio.run(setup())

    app.run(
        host="0.0.0.0",
        port=PORT
                )
