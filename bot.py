import os
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ======================
# الإعدادات
# ======================
TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", 10000))

ADMIN_IDS = list(map(int, os.environ.get("ADMIN_IDS", "").split(","))) if os.environ.get("ADMIN_IDS") else []

# ======================
# حماية الأخطاء
# ======================
if not TOKEN:
    raise ValueError("❌ BOT_TOKEN غير موجود في Render Environment Variables")

if not WEBHOOK_URL:
    raise ValueError("❌ WEBHOOK_URL غير موجود في Render Environment Variables")

# ======================
# قاعدة البيانات
# ======================
conn = sqlite3.connect("students.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    status TEXT
)
""")
conn.commit()

# ======================
# وظائف قاعدة البيانات
# ======================
def set_student(user_id, name, status):
    cursor.execute("""
    INSERT INTO students (user_id, name, status)
    VALUES (?, ?, ?)
    ON CONFLICT(user_id) DO UPDATE SET
    name=excluded.name,
    status=excluded.status
    """, (user_id, name, status))
    conn.commit()


def remove_student(user_id):
    cursor.execute("DELETE FROM students WHERE user_id=?", (user_id,))
    conn.commit()


def clear_all():
    cursor.execute("DELETE FROM students")
    conn.commit()


def get_all():
    cursor.execute("SELECT name, status FROM students")
    return cursor.fetchall()

# ======================
# حالة التسجيل
# ======================
registration_open = True


def is_admin(user_id: int):
    return user_id in ADMIN_IDS

# ======================
# لوحة الأزرار
# ======================
def keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ قرأت", callback_data="read"),
            InlineKeyboardButton("🎧 مستمعة", callback_data="listen"),
        ],
        [
            InlineKeyboardButton("🚫 معتذرة", callback_data="excuse"),
            InlineKeyboardButton("❌ حذف اسمي", callback_data="remove"),
        ],
        [
            InlineKeyboardButton("🔒 قفل/فتح", callback_data="toggle"),
            InlineKeyboardButton("🧹 تصفير", callback_data="clear"),
        ],
    ])

# ======================
# عرض الحالة
# ======================
def get_status():
    date_now = datetime.now().strftime("%Y-%m-%d")
    data = get_all()

    text = f"""🤖 بوت الأكاديمية
📅 التاريخ: {date_now}

🔒 التسجيل: {'مفتوح ✅' if registration_open else 'مغلق ⛔'}

-----------------------
"""

    categories = {
        "read": "📘 قرأت",
        "listen": "🎧 مستمعة",
        "excuse": "🚫 معتذرة"
    }

    for key, title in categories.items():
        text += f"\n{title}:\n"
        items = [n for n, s in data if s == key]
        text += "\n".join([f"• {i}" for i in items]) if items else "لا يوجد"
        text += "\n"

    text += "\n-----------------------\n📚 استمر في التعلم"
    return text

# ======================
# /start
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_status(), reply_markup=keyboard())

# ======================
# الأزرار
# ======================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global registration_open

    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    name = query.from_user.full_name
    data = query.data

    if data in ["read", "listen", "excuse"]:
        if registration_open:
            set_student(user_id, name, data)

    elif data == "remove":
        remove_student(user_id)

    elif data == "toggle":
        if is_admin(user_id):
            registration_open = not registration_open
        else:
            await query.answer("خاص بالمشرفين فقط", show_alert=True)

    elif data == "clear":
        if is_admin(user_id):
            clear_all()
