from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os

TOKEN = os.environ["BOT_TOKEN"]

app = Application.builder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("البوت يعمل ✔")

app.add_handler(CommandHandler("start", start))

if __name__ == "__main__":
    print("BOT RUNNING")
    app.run_polling()
