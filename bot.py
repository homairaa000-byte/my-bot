 import os
import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = os.getenv("BASE_URL")  # رابط Render https://xxxx.onrender.com
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = BASE_URL + WEBHOOK_PATH

logging.basicConfig(level=logging.INFO)

# =========================
# FLASK APP
# =========================
app = Flask(__name__)

# =========================
# BOT SETUP
# =========================
application = Application.builder().token(TOKEN).build()

# =========================
# HANDLERS
# =========================
async def start(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("📜 القوانين", callback_data="rules")],
        [InlineKeyboardButton("📅 الجدول", callback_data="schedule")]
    ]

    await update.message.reply_text(
        "👋 أهلاً بك في البوت",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def buttons(update: Update, context):
    query = update.callback_query
    await query.answer()

    if query.data == "rules":
        await query.edit_message_text(
            "📜 القوانين:\n- احترام الجميع\n- عدم السب\n- الالتزام"
        )

    elif query.data == "schedule":
        await query.edit_message_text(
            "📅 الجدول:\n- تحديثات يومية\n- محتوى مستمر"
        )


# تسجيل الهاندلرز
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(buttons))

# =========================
# WEBHOOK ROUTE
# =========================
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    application.process_update(update)
    return "OK"


# فحص السيرفر
@app.route("/")
def home():
    return "Bot is running via Webhook ✅"


# =========================
# SET WEBHOOK ON START
# =========================
@app.before_first_request
def setup_webhook():
    logging.info(f"Setting webhook: {WEBHOOK_URL}")
    application.bot.set_webhook(url=WEBHOOK_URL)


# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
