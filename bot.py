import os
from datetime import datetime
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
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
        text += "\n".join([f"• {n}" for n in names]) if names else "لا يوجد"
        text += "\n"

    return text


async def start(update, context):
    keyboard = [
        [InlineKeyboardButton("✅ قرأت", callback_data="read"),
         InlineKeyboardButton("🎧 مستمعة", callback_data="listen")],

        [InlineKeyboardButton("🚫 معتذرة", callback_data="excuse"),
         InlineKeyboardButton("❌ حذف اسمي", callback_data="remove")],

        [InlineKeyboardButton("🔒 قفل/فتح", callback_data="toggle"),
         InlineKeyboardButton("🧹 تصفير", callback_data="clear")],

        [InlineKeyboardButton("🚫 حظر طالبة", callback_data="ban")]
    ]

    await update.message.reply_text(
        get_status(),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def buttons(update, context):
    global registration_open

    query = update.callback_query
    await query.answer()

    user = query.from_user.full_name
    data = query.data

    if user in students["محظورات"]:
        await query.answer("أنتِ محظورة من النظام!", show_alert=True)
        return

    if data in ["read", "listen", "excuse"] and registration_open:

        for cat in students:
            if user in students[cat]:
                students[cat].remove(user)

        if data == "read":
            students["قرأت"].append(user)
        elif data == "listen":
            students["مستمعة"].append(user)
        elif data == "excuse":
            students["معتذرة"].append(user)

    elif data == "remove":
        for cat in students:
            if user in students[cat]:
                students[cat].remove(user)

    elif data == "toggle":
        registration_open = not registration_open

    elif data == "clear":
        for cat in students:
            if cat != "محظورات":
                students[cat] = []

    elif data == "ban":
        await query.message.reply_text("ردي بكلمة 'حظر' على اسم الطالبة")

    await query.edit_message_text(get_status())


@app.route(f"/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run(application.process_update(update))
    return "ok"


@app.route("/")
def home():
    return "Bot is running!"


async def setup():
    await application.initialize()
    await application.bot.set_webhook(
        url=f"{WEBHOOK_URL}/webhook"
    )


if __name__ == "__main__":

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(buttons))

    asyncio.run(setup())

    app.run(host="0.0.0.0", port=PORT)
