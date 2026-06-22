import os
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

app = Flask(__name__)

telegram_app = Application.builder().token(TOKEN).build()


# =====================
# أوامر البوت
# =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 البوت يعمل بنظام Webhook على Render")


telegram_app.add_handler(CommandHandler("start", start))


# =====================
# Webhook Route
# =====================
@app.route("/webhook", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    await telegram_app.process_update(update)
    return "ok"


# =====================
# تشغيل السيرفر
# =====================
@app.route("/")
def home():
    return "Bot is running"


def main():
    telegram_app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        webhook_url=WEBHOOK_URL
    )


if __name__ == "__main__":
    main()
