import os
import asyncio
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

TOKEN = '8817548868:AAHA4NrB7j28k7xSoIe2EVd3nZjZoA_rHJY'
PORT = int(os.environ.get('PORT', 8080))
WEBHOOK_URL = 'https://my-bot-pwus.onrender.com'

app = Flask(__name__)
# إنشاء التطبيق
application = Application.builder().token(TOKEN).build()

# بيانات البوت
students = {"قرأت": [], "مستمعة": [], "معتذرة": []}
registration_open = True

def get_status():
    status = "مفتوح ✅" if registration_open else "مغلق ⛔"
    text = f"🔒 التسجيل: {status}\n\n📋 **قائمة الطالبات:**\n"
    for cat, names in students.items():
        text += f"\n{cat}:\n" + ("\n".join(names) if names else "لا يوجد")
    return text

async def start(update, context):
    keyboard
