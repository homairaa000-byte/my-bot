import os
import sqlite3
import asyncio
from datetime import datetime
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# قاعدة البيانات
conn = sqlite3.connect("students.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS students (user_id INTEGER PRIMARY KEY, name TEXT, status TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS banned (user_id INTEGER PRIMARY KEY, name TEXT)")
conn.commit()

async def is_admin(update, context):
    try:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        admins = await context.bot.get_chat_administrators(chat_id)
        return any(admin.user.id == user_id for admin in admins)
    except: return False

def get_status_text():
    cursor.execute("SELECT name, status FROM students")
    data = cursor.fetchall()
    cursor.execute("SELECT name FROM banned")
    banned_list = [row[0] for row in cursor.fetchall()]
    
    date = datetime.now().strftime('%Y-%m-%d')
    text = f"خادم القرآن الرقمي\n📋 قائمة تسجيل الأدوار\n📅 {date}\n\n"
    
    # خانة المسجلات (التي تحتوي على علامة الصح)
    text += "✍️ المسجلات:\n"
    for n, s in data:
        check = " ✅" if s == "read" else ""
        text += f"• {n}{check}\n"
    
    text += f"\n🎧 مستمعات:\n" + "\n".join([f"• {n}" for n, s in data if s == "listen"])
    text += f"\n\n⛔️ معتذرات:\n" + "\n".join([f"• {n}" for n, s in data if s == "exc
