from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📜 القوانين", callback_data="rules")],
        [InlineKeyboardButton("📅 الجدول", callback_data="schedule")],
        [InlineKeyboardButton("ℹ️ الترحيب", callback_data="welcome")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 أهلاً بك في أكاديمية معارج الإتقان\n\nاختر من القائمة:",
        reply_markup=reply_markup
    )
