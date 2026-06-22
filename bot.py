import asyncio
from flask import Flask, request

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import TOKEN, WEBHOOK_URL
from database import init_db, add_user

app = Flask(__name__)

# ===== Bot Application =====
bot_app = Application.builder().token(TOKEN).build()


# ===== /start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await add_user(user_id)

    await update.message.reply_text("👋 أهلاً بك! البوت يعمل بنجاح 🚀")


bot_app.add_handler(CommandHandler("start", start))


# ===== Webhook Route =====
@app.post(f"/{TOKEN}")
def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    bot_app.process_update(update)
    return "ok"


# ===== تشغيل البوت =====
async def run():
    await init_db()

    await bot_app.initialize()
    await bot_app.start()

    await bot_app.bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")

    print("🚀 Bot is running with Webhook")

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(run())
