import os
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = '8817548868:AAHA4NrB7j28k7xSoIe2EVd3nZjZoA_rHJY'
PORT = int(os.environ.get('PORT', 8080))
WEBHOOK_URL = 'https://my-bot-pwus.onrender.com' 

app = Flask(__name__)
bot = Bot(TOKEN)
application = Application.builder().token(TOKEN).build()

# قاموس لتخزين الأسماء والحالات: {اسم الطالبة: الحالة}
students = {}
banned_users = [] # قائمة المحظورات

def get_list_text():
    # تقسيم الأسماء حسب الحالات
    readers = [f"✅ {name}" for name, status in students.items() if status == "قرأت"]
    listeners = [name for name, status in students.items() if status == "مستمعة"]
    absents = [name for name, status in students.items() if status == "معتذرة"]
    
    text = "📋 **قائمة الإسم الثلاثي للطالبات**\n\n"
    text += "✅ **القارئات:**\n" + ("\n".join(readers) if readers else "لا يوجد") + "\n\n"
    text += "🎧 **المستمعات:**\n" + ("\n".join(listeners) if listeners else "لا يوجد") + "\n\n"
    text += "⛔ **المعتذرات:**\n" + ("\n".join(absents) if absents else "لا يوجد")
    return text

async def start(update, context):
    user = update.effective_user.full_name
    if user in banned_users:
        await update.message.reply_text("🚫 عذراً، اسمك موجود في قائمة الحظر.")
        return
    
    # تسجيل الطالبة أول مرة إذا لم تكن موجودة
    if user not in students:
        students[user] = "مسجلة"
    
    keyboard = [
        [InlineKeyboardButton("✅ قرأت", callback_data='read'), InlineKeyboardButton("🎧 مستمعة", callback_data='listen')],
        [InlineKeyboardButton("⛔ معتذرة", callback_data='absent'), InlineKeyboardButton("❌ حذف اسمي", callback_data='remove')]
    ]
    await update.message.reply_text(get_list_text(), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def button(update, context):
    query = update.callback_query
    user = query.from_user.full_name
    
    if query.data == 'read': students[user] = "قرأت"
    elif query.data == 'listen': students[user] = "مستمعة"
    elif query.data == 'absent': students[user] = "معتذرة"
    elif query.data == 'remove':
        if user in students: del students[user]
    
    await query.edit_message_text(text=get_list_text(), reply_markup=query.message.reply_markup, parse_mode='Markdown')
    await query.answer("تم تحديث القائمة!")

async def ban_command(update, context):
    if update.message.reply_to_message:
        banned_name = update.message.reply_to_message.from_user.full_name
        banned_users
