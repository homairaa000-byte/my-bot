import os
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", 10000))


# =========================
# BOT CORE
# =========================
app = Application.builder().token(TOKEN).build()


# =========================
# COMMANDS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 البوت يعمل بنجاح على Webhook (V5 احترافي)\n"
        "📡 جاهز للاستضافة على Render"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 الأوامر المتاحة:\n"
        "/start - تشغيل البوت\n"
        "/help - المساعدة"
    )


app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_cmd))


# =========================
# WEBHOOK SETUP
# =========================
async def post_init(application: Application):
    await application.bot.set_webhook(WEBHOOK_URL)


app.post_init = post_init


# =========================
# RUN SERVER
# =========================
def main():
    print("🚀 Bot V5 Webhook is running...")

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL,
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
