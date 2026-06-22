import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from handlers.start import start

# =========================
# SETTINGS
# =========================
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")


# =========================
# START BUTTON HANDLER
# =========================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "rules":
        await query.edit_message_text("📜 القوانين سيتم إضافتها قريبًا")

    elif query.data == "schedule":
        await query.edit_message_text("📅 الجدول سيتم إضافته قريبًا")

    elif query.data == "welcome":
        await query.edit_message_text("🌿 أهلاً بك في الأكاديمية")


# =========================
# MAIN
# =========================
def main():
    app = Application.builder().token(TOKEN).build()

    # أوامر
    app.add_handler(CommandHandler("start", start))

    # أزرار
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot is running...")

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
