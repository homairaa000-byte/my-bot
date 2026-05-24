import os
import sqlite3
import re
import asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

conn = sqlite3.connect("students.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS students (user_id INTEGER PRIMARY KEY, name TEXT, status TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
cursor.execute("INSERT OR IGNORE INTO settings VALUES ('locked','false')")
conn.commit()

def locked():
    return cursor.execute("SELECT value FROM settings WHERE key='locked'").fetchone()[0] == "true"

async def is_admin(user_id, chat_id):
    try:
        admins = await application.bot.get_chat_administrators(chat_id)
        return any(a.user.id == user_id for a in admins)
    except:
        return False

def text():
    cursor.execute("SELECT name,status FROM students")
    data = cursor.fetchall()

    out = "📚 قائمة التسجيل\n\n"
    for key,title in [("register","تسجيل"),("read","قرأ"),("listen","استماع"),("excuse","اعتذار")]:
        out += f"{title}:\n"
        names = [n for n,s in data if s == key]
        out += "\n".join(names) if names else "لا يوجد"
        out += "\n\n"

    return out

async def keyboard(update):
    kb = [
        [InlineKeyboardButton("تسجيل", callback_data="register")],
        [InlineKeyboardButton("قرأ", callback_data="read"), InlineKeyboardButton("استماع", callback_data="listen")],
        [InlineKeyboardButton("اعتذار", callback_data="excuse")]
    ]
    return InlineKeyboardMarkup(kb)

async def start(update, context):
    await update.message.reply_text(text(), reply_markup=await keyboard(update))

async def buttons(update, context):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    name = q.from_user.full_name
    data = q.data

    if data in ["register","read","listen","excuse"]:
        if locked() and not await is_admin(uid, q.message.chat.id):
            await q.answer("التسجيل مغلق", show_alert=True)
            return
        cursor.execute("INSERT OR REPLACE INTO students VALUES (?,?,?)", (uid,name,data))

    conn.commit()
    await q.edit_message_text(text(), reply_markup=await keyboard(update))

@app.route("/")
def home():
    return "BOT OK"

@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run(application.process_update(update))
    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
