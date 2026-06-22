import os
import asyncio
import asyncpg
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 10000))
DATABASE_URL = os.getenv("DATABASE_URL")

if not TOKEN:
    raise ValueError("BOT_TOKEN is missing")
if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL is missing")


# =========================
# APPLICATION
# =========================
app = Application.builder().token(TOKEN).build()


# =========================
# ADMIN CHECK
# =========================
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id,
            update.effective_user.id
        )
        return member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except:
        return False


# =========================
# DATABASE
# =========================
async def get_db():
    return await asyncpg.connect(DATABASE_URL)


async def get_locked(chat_id):
    conn = await get_db()
    await conn.execute("""
        INSERT INTO groups(chat_id, locked)
        VALUES($1, FALSE)
        ON CONFLICT (chat_id) DO NOTHING
    """, chat_id)

    row = await conn.fetchrow(
        "SELECT locked FROM groups WHERE chat_id=$1",
        chat_id
    )
    await conn.close()
    return row["locked"] if row else False


# =========================
# TEXTS (UNCHANGED)
# =========================
WELCOME_MESSAGE = """
مرحبا مرحبا بوصية رسول الله...
قال رسول الله ﷺ: "سيأتيكُم أقوامٌ يطلبونَ العِلمَ، فإذا رأيتُموهم فقولوا لَهُم: مَرحبًا مَرحبًا بوصيَّةِ رسولِ اللَّهِ صلَّى اللَّهُ عليهِ وسلَّمَ، واقْنوهُم". قلتُ للحَكَمِ: ما اقْنوهُم؟ قالَ: علِّموهُم.

أهلاً بكِ في أكاديمية معارج الإتقان 🕊🌴🌴🌴
"""

RULES_TEXT = """
بسم الله الرحمن الرحيم 

أكاديمية معارج الاتقان 🕊🌴🌴🌴

قوانين الأكاديمية:

🌴🌴الأكاديمية تعنى بتقديم كل ما يتعلق بالتجويد والقران من حصص تجويد وتصحيح تلاوه وقراءات وغيرها من المجالات. 

1. الأكاديمية خاصه بالنساء فقط 🚫

2. الإنضباط هو الشرط الأساسي 👩‍✈️

3. كتابة الاسم بوضوح ❌

4. مجموعات الحفظ برواية قالون:
- ربع يس: أم ساجدة
- ربع البقرة: مريم
- جزء عم وتبارك: يسر ورغي

5. مجموعات حفص:
- ربع يس: نهى سعيد
- تبارك وعم: فاطمة فتحي
- ربع البقرة: زهراء وأماني وميمونة

6. لا توجد ورش حالياً

7. ممنوع الروابط 🛑

8. ممنوع التواصل الخاص ✋
"""

SCHEDULE_TEXT = """
✍ جدول حلقات المقرأة

💐 لطيفة - تصحيح تلاوة (الاثنين 12)
💐 لطيفة - مخارج (الثلاثاء 12)
💐 لطيفة - الأربعاء (12)
💐 عالية محمد - 6 مساء
💐 مريم ياسين - 3 ليبيا

🍃 القرآن نافع في الدنيا والقبر والجنة
"""

HELP_TEXT = """
/start - تشغيل البوت
/help - المساعدة
/ban - حظر (رد)
/unban - فك حظر (رد)
"""


# =========================
# MENU
# =========================
def menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✍️ سجل اسمي", callback_data="register"),
            InlineKeyboardButton("🎧 مستمعة", callback_data="listener")
        ],
        [
            InlineKeyboardButton("⛔️ معتذرة", callback_data="excused"),
            InlineKeyboardButton("❌ حذف", callback_data="remove")
        ],
        [
            InlineKeyboardButton("🔒 قفل/فتح", callback_data="lock"),
            InlineKeyboardButton("🧹 تصفير", callback_data="reset")
        ],
        [
            InlineKeyboardButton("📜 القوانين", callback_data="rules"),
            InlineKeyboardButton("📅 الجدول", callback_data="schedule")
        ],
        [
            InlineKeyboardButton("✅ قرأت", callback_data="read")
        ]
    ])


# =========================
# BUILD MESSAGE
# =========================
async def build(chat_id):
    conn = await get_db()

    locked = await get_locked(chat_id)

    data = await conn.fetch("""
        SELECT name,status,read_status
        FROM users
        WHERE chat_id=$1
        ORDER BY created_at ASC
    """, chat_id)

    await conn.close()

    def section(status):
        result = [
            f"{row['name']}{' ✅' if row['read_status'] else ''}"
            for row in data if row["status"] == status
        ]
        return "\n".join(result) if result else "لا يوجد"

    return (
        "السلام عليكم ورحمة الله وبركاته\n"
        f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        "خادم القرآن الرقمي 💫\n"
        f"{'🔒 مغلق' if locked else '🔓 مفتوح'}\n\n"
        f"✍ المسجلات:\n{section('register')}\n\n"
        f"🎧 المستمعات:\n{section('listener')}\n\n"
        f"⛔ المعتذرات:\n{section('excused')}\n\n"
        f"🚫 المحظورات:\n{section('banned')}\n\n"
        "وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا"
    )


# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = await build(update.effective_chat.id)
    await update.message.reply_text(text, reply_markup=menu())


# =========================
# HELP
# =========================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)


# =========================
# BAN / UNBAN
# =========================
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return

    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user

        conn = await get_db()
        await conn.execute("""
            INSERT INTO users(chat_id,user_id,name,status,read_status,created_at)
            VALUES($1,$2,$3,'banned',FALSE,$4)
            ON CONFLICT (chat_id,user_id)
            DO UPDATE SET status='banned'
        """, update.effective_chat.id, target.id, target.full_name, datetime.now())

        await conn.close()
        await update.message.reply_text(f"🚫 تم حظر {target.full_name}")


async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return

    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user

        conn = await get_db()
        await conn.execute(
            "DELETE FROM users WHERE chat_id=$1 AND user_id=$2",
            update.effective_chat.id,
            target.id
        )
        await conn.close()

        await update.message.reply_text(f"✅ تم فك الحظر عن {target.full_name}")


# =========================
# BUTTONS
# =========================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    chat_id = q.message.chat_id
    user_id = q.from_user.id
    name = q.from_user.full_name
    action = q.data

    conn = await get_db()

    status = await conn.fetchrow(
        "SELECT status FROM users WHERE chat_id=$1 AND user_id=$2",
        chat_id, user_id
    )

    if status and status["status"] == "banned":
        await conn.close()
        return

    if action in ["register", "listener", "excused"]:
        if await get_locked(chat_id):
            await conn.close()
            return

        await conn.execute("""
            INSERT INTO users(chat_id,user_id,name,status,read_status,created_at)
            VALUES($1,$2,$3,$4,FALSE,$5)
            ON CONFLICT (chat_id,user_id)
            DO UPDATE SET status=$4
        """, chat_id, user_id, name, action, datetime.now())

    elif action == "remove":
        await conn.execute(
            "DELETE FROM users WHERE chat_id=$1 AND user_id=$2",
            chat_id, user_id
        )

    elif action == "read":
        await conn.execute(
            "UPDATE users SET read_status = NOT read_status WHERE chat_id=$1 AND user_id=$2",
            chat_id, user_id
        )

    elif action == "lock":
        if await is_admin(update, context):
            await conn.execute(
                "UPDATE groups SET locked = NOT locked WHERE chat_id=$1",
                chat_id
            )

    elif action == "reset":
        if await is_admin(update, context):
            await conn.execute(
                "DELETE FROM users WHERE chat_id=$1 AND status!='banned'",
                chat_id
            )

    await conn.close()

    try:
        await q.edit_message_text(await build(chat_id), reply_markup=menu())
    except:
        pass


# =========================
# HANDLERS
# =========================
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("ban", ban))
app.add_handler(CommandHandler("unban", unban))
app.add_handler(CallbackQueryHandler(buttons))


# =========================
# RUN (FIXED WEBHOOK RENDER)
# =========================
if __name__ == "__main__":
    print("🚀 BOT RUNNING ON RENDER (PRODUCTION)")

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
                         )
