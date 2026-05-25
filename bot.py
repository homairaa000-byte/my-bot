import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# 🔐 التوكن من Railway Variables
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise Exception("BOT_TOKEN is missing in Railway Variables")

# 📌 بيانات بسيطة (مؤقتة داخل الذاكرة)
students = set()
blocked = set()
registration_open = True


# =========================
# 🎛️ لوحة الأزرار
# =========================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ سجل إسمي", callback_data="register")],
        [InlineKeyboardButton("❌ إحذف إسمي", callback_data="remove")],
        [InlineKeyboardButton("✅ قرأت", callback_data="read")],
        [InlineKeyboardButton("🚫 محظورات", callback_data="blocked")]
    ])


# =========================
# 🚀 /start
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "السلام عليكم ورحمة الله وبركاته\n\n"
        "📖 خادم القرآن الرقمي\n\n"
        "﴿ وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ۚ وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ ﴾\n\n"
        f"📅 {datetime.now().strftime('%Y-%m-%d')}"
    )
    await update.message.reply_text(text, reply_markup=main_menu())


# =========================
# 🎛️ التعامل مع الأزرار
# =========================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global registration_open
    query = update.callback_query
    await query.answer()

    user = query.from_user.full_name

    # 🚫 محظور
    if user in blocked:
        await query.message.reply_text("🚫 أنتِ محظورة")
        return

    # ✍️ تسجيل
    if query.data == "register":
        if registration_open:
            students.add(user)
            await query.message.reply_text(f"✔ تم تسجيل: {user}")
        else:
            await query.message.reply_text("⛔ التسجيل مغلق")

    # ❌ حذف الاسم
    elif query.data == "remove":
        students.discard(user)
        await query.message.reply_text("❌ تم حذف اسمك")

    # 📖 قرأت
    elif query.data == "read":
        await query.message.reply_text(f"📖 {user} قرأت اليوم")

    # 🚫 عرض المحظورات
    elif query.data == "blocked":
        text = "\n".join(blocked) if blocked else "لا يوجد محظورات"
        await query.message.reply_text("🚫 القائمة:\n" + text)


# =========================
# 🚫 منع الروابط
# =========================
async def block_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text:
        text = update.message.text.lower()

        if "http" in text or "www" in text:
            try:
                await update.message.delete()
            except:
                pass

            await update.message.reply_text(
                "⛔️⛔️⛔️ إرسال روابط من دون الرجوع للإشراف يعرضك للحذف"
            )


#
