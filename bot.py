import os
import sqlite3
import re
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ================= TOKEN =================
TOKEN = os.environ.get("BOT_TOKEN")

application = Application.builder().token(TOKEN).build()

# ================= DATABASE =================
conn = sqlite3.connect("students.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    status TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS banned (
    user_id INTEGER PRIMARY KEY,
    name TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")

cursor.execute("INSERT OR IGNORE INTO settings VALUES ('locked','false')")
conn.commit()

# ================= TIME =================
def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")

# ================= ADMIN CHECK =================
async def is_admin(user_id, chat_id):
    try:
        admins = await application.bot.get_chat_administrators(chat_id)
        return any(a.user.id == user_id for a in admins)
    except:
        return False

# ================= TEXT =================
def get_text():
    cursor.execute("SELECT name, status FROM students")
    students = cursor.fetchall()

    cursor.execute("SELECT name FROM banned")
    banned = [x[0] for x in cursor.fetchall()]

    text = (
        "السلام عليكم ورحمة الله وبركاته\n\n"
        "📚 خادم القرآن الرقمي\n\n"
        f"🕒 {now()}\n\n"
    )

    cats = {
        "register": "✍️ المسجلات",
        "read": "✅ قرأت",
        "listen": "🎧 مستمعات",
        "excuse": "⛔️ معتذرات"
    }

    for key, title in cats.items():
        text += f"{title}:\n"
        names = [n for n, s in students if s == key]
        text += "\n".join(f"• {n}" for n in names) if names else "لا يوجد"
        text += "\n\n"

    text += "🚫 المحظورات:\n"
    text += "\n".join(f"• {n}" for n in banned) if banned else "لا يوجد"

    text += "\n\nوَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ۚ وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ"

    return text

# ================= KEYBOARD =================
async def keyboard(update: Update):
    buttons = [
        [
            InlineKeyboardButton("✍ سجل إسمي", callback_data="register"),
            InlineKeyboardButton("❌ إحذف إسمي", callback_data="remove"),
        ],
        [
            InlineKeyboardButton("✅ قرأت", callback_data="read"),
            InlineKeyboardButton("🎧 مستمعات", callback_data="listen"),
        ],
        [
            InlineKeyboardButton("⛔️ معتذرات", callback_data="excuse"),
        ],
    ]

    if await is_admin(update.effective_user.id, update.effective_chat.id):
        buttons.append([
            InlineKeyboardButton("🔒 قفل/فتح التسجيل", callback_data="toggle"),
            InlineKeyboardButton("🗑 تصفير القائمة", callback_data="clear"),
        ])

    return InlineKeyboardMarkup(buttons)

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_text(), reply_markup=await keyboard(update))

# ================= BLOCK LINKS =================
async def block_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if re.search(r"http|www|t\.me", update.message.text or ""):
        if not await is_admin(update.effective_user.id, update.effective_chat.id):
            await update.message.delete()
            await update.message.reply_text(
                "⛔️⛔️⛔️ إرسال روابط من دون الرجوع للإشراف يعرضك للحذف"
            )

# ================= BUTTONS =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        cursor.execute("SELECT name FROM banned WHERE user_id=?", (uid,))
        if cursor.fetchone():
            await q.answer("أنتِ في قائمة المحظورات 🚫", show_alert=True)
            return

        if locked == "true" and not await is_admin(uid, q.message.chat.id):
            await q.answer("التسجيل مقفل", show_alert=True)
            return

        cursor.execute(
            "INSERT OR REPLACE INTO students VALUES (?, ?, ?)",
            (uid, name, data),
        )

    conn.commit()

    await q.edit_message_text(get_text(), reply_markup=await keyboard(update))

# ================= HANDLERS =================
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, block_links))
application.add_handler(CallbackQueryHandler(buttons))

# ================= RUN (POLLING ONLY) =================
if __name__ == "__main__":
    print("🚀 Bot running (Polling mode - stable)")
    application.run_polling(drop_pending_updates=True)
