import os
import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = os.getenv("BASE_URL")  # https://your-app.onrender.com
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}"

logging.basicConfig(level=logging.INFO)

# =========================
# FLASK APP
# =========================
app = Flask(__name__)

# =========================
# TELEGRAM APP
# =========================
application = Application.builder().token(TOKEN).build()

# =========================
# START COMMAND
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

# =========================
# CALLBACK BUTTONS
# =========================
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

# =========================
# REGISTER HANDLERS
# =========================
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(buttons))

# =========================
# WEBHOOK ENDPOINT
# =========================
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    application.process_update(update)
    return "OK"

# =========================
# HEALTH CHECK (Render)
# =========================
@app.route("/")
def home():
    return "Bot is running via Webhook ✅"

# =========================
# SETUP WEBHOOK (ON START)
# =========================
def set_webhook():
    import requests
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    requests.get(url, params={"url": WEBHOOK_URL})
    logging.info(f"Webhook set to: {WEBHOOK_URL}")

# =========================
# INIT BOT
# =========================
with application:
    application.initialize()
    set_webhook()

# =========================
# RUN SERVER
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
