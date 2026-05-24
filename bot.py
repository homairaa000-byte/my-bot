import os
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ======================
# إعدادات آمنة
# ======================
TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", 10000))

# 🔥 حماية من خطأ ADMIN_IDS الفارغ
raw_admins = os.environ.get("ADMIN_IDS", "")
ADMIN_IDS = list(map(int, raw_admins.split(","))) if raw_admins.strip() else []

# ======================
# تحقق من الإعدادات
# ======================
if not TOKEN:
    raise ValueError("BOT_TOKEN is missing in environment variables")

if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL is missing in environment variables")

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
# أدوات قاعدة البيانات
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


def is_admin(user_id: int):
    return user_id in ADMIN_IDS


# ======================
# عرض الحالة
# ======================
def get_status():
    date_now = datetime.now().strftime("%Y-%m-%d")
    data = get_all()

    text = f"""
🤖 مساعد الأكاديمية
📅 التاريخ: {date_now}

🔒 التسجيل: {'مفتوح ✅' if registration_open else 'مغلق ⛔'}

-----------------------
"""

    categories = {"read": "قرأت", "listen": "مستمعة", "excuse": "معتذرة"}

    for key, title in categories.items():
        text += f"\n{title}:\n"
        items = [n for n, s in data if s == key]
        text += "\n".join([f"• {i}" for i in items]) if items else "لا يوجد"
        text += "\n"

    text += "\n-----------------------\n📖 استمر في التعلم"
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

    # تسجيل الحالات
    if data in ["read", "listen", "excuse"]:
        if registration_open:
            set_student(user_id, name, data)

    elif data == "remove":
        remove_student(user_id)

    # أوامر الأدمن
    elif data == "toggle":
        if is_admin(user_id):
            registration_open = not registration_open
        else:
            await query.answer("خاص بالمشرفين فقط", show_alert=True)

    elif data == "clear":
        if is_admin(user_id):
            clear_all()
        else:
            await query.answer("خاص بالمشرفين فقط", show_alert=True)

    # تحديث الرسالة
    await query.edit_message_text(get_status(), reply_markup=keyboard())


# ======================
# تشغيل Webhook (Render)
# ======================
async def post_init(app: Application):
    await app.bot.set_webhook(f"{WEBHOOK_URL}/webhook")


def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="webhook",
    )


if __name__ == "__main__":
    main()
