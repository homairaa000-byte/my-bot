import os
import sqlite3
import re
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

TOKEN = os.environ.get("BOT_TOKEN")

# ================== DB ==================
conn = sqlite3.connect("students.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS students (user_id INTEGER PRIMARY KEY, name TEXT, status TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS banned (user_id INTEGER PRIMARY KEY, name TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
cursor.execute("INSERT OR IGNORE INTO settings VALUES ('locked', 'false')")
conn.commit()

# ================== BOT ==================
application = Application.builder().token(TOKEN).build()

# ================== ADMIN CHECK ==================
async def is_admin(user_id, chat_id):
    try:
        admins = await application.bot.get_chat_administrators(chat_id)
        return any(a.user.id == user_id for a in admins)
    except:
        return False

# ================== TEXT ==================
def get_status_text():
    cursor.execute("SELECT name, status FROM students")
    data = cursor.fetchall()

    cursor.execute("SELECT name FROM banned")
    banned = [r[0] for r in cursor.fetchall()]

    text = "📚 خادم القرآن الرقمي\n\n"

    cats = {
        "register": "✍️ المسجلات",
        "read": "✅ قرأت",
        "listen": "🎧 مستمعات",
        "excuse": "⛔ معتذرات"
    }

    for key, title in cats.items():
        text += f"{title}:\n"
        names = [n for n, s in data if s == key]
        text += "\n".join(f"• {n}" for n in names) if names else "لا يوجد"
        text += "\n\n"

    text += "🚫 المحظورات:\n"
    text += "\n".join(f"• {n}" for n in banned) if banned else "لا يوجد"

    return text

# ================== KEYBOARD ==================
async def get_keyboard(update):
    kb = [
        [InlineKeyboardButton("✍ سجل", callback_data="register"),
         InlineKeyboardButton("❌ حذف اسمي", callback_data="remove")],
        [InlineKeyboardButton("✅ قرأت", callback_data="read"),
         InlineKeyboardButton("🎧 مستمع", callback_data="listen")],
        [InlineKeyboardButton("⛔ معتذر", callback_data="excuse")]
    ]

    if await is_admin(update.effective_user.id, update.effective_chat.id):
        kb.append([
            InlineKeyboardButton("🔒 قفل/فتح", callback_data="toggle"),
            InlineKeyboardButton("🗑 تصفير", callback_data="clear")
        ])

    return InlineKeyboardMarkup(kb)

# ================== START ==================
async def start(update: Update, context):
    await update.message.reply_text(
        get_status_text(),
        reply_markup=await get_keyboard(update)
    )

# ================== LINK FILTER ==================
async def link_filter(update: Update, context):
    if update.message and update.message.text:
        if re.search(r"http|www|t\.me", update.message.text):
            if not await is_admin(update.effective_user.id, update.effective_chat.id):
                await update.message.delete()

# ================== BUTTONS ==================
async def handle_buttons(update: Update, context):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    name = q.from_user.full_name
    data = q.data

    locked = cursor.execute("SELECT value FROM settings WHERE key='locked'").fetchone()[0]

    if data == "toggle":
        new = "false" if locked == "true" else "true"
        cursor.execute("UPDATE settings SET value=? WHERE key='locked'", (new,))

    elif data == "clear":
        cursor.execute("DELETE FROM students")

    elif data == "remove":
        cursor.execute("DELETE FROM students WHERE user_id=?", (uid,))

    elif data in ["register", "read", "listen", "excuse"]:
        if locked == "true":
            await q.answer("التسجيل مقفل", show_alert=True)
            return

        cursor.execute(
            "INSERT OR REPLACE INTO students VALUES (?, ?, ?)",
            (uid, name, data)
        )

    conn.commit()

    await q.edit_message_text(
        get_status_text(),
        reply_markup=await get_keyboard(update)
    )

# ================== HANDLERS ==================
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, link_filter))
application.add_handler(CallbackQueryHandler(handle_buttons))

# ================== MAIN (POLLING) ==================
if __name__ == "__main__":
    print("🤖 Bot is running in POLLING mode...")

    application.run_polling(
        drop_pending_updates=True
    )
