import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # مثال: https://your-app.onrender.com
PORT = int(os.getenv("PORT", 10000))

logging.basicConfig(level=logging.INFO)

app_flask = Flask(__name__)

# =========================
# TELEGRAM APP
# =========================
telegram_app = Application.builder().token(TOKEN).build()


# =========================
# HANDLERS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 البوت يعمل بنجاح (Webhook Mode)")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(update.message.text)


telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))


# =========================
# WEBHOOK ENDPOINT
# =========================
@app_flask.post(f"/{TOKEN}")
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app)
    telegram_app.update_queue.put_nowait(update)
    return "ok"


@app_flask.get("/")
def home():
    return "Bot is running ✔"


# =========================
# STARTUP
# =========================
def set_webhook():
    url = f"{WEBHOOK_URL}/{TOKEN}"
    telegram_app.bot.set_webhook(url=url)
    print("Webhook set:", url)


if __name__ == "__main__":
    set_webhook()
    app_flask.run(host="0.0.0.0", port=PORT)
