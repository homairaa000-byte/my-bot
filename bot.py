import os
import asyncio
import asyncpg
import threading
from datetime import datetime
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# =========================
# SETTINGS
# =========================
# يتم جلب التوكن من متغيرات البيئة في تيرموكس
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

bot_app = Application.builder().token(TOKEN).build()

# =========================
# HELPER: Check Admin
# =========================
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except:
        return False

# =========================
# DATABASE & BUILD
# =========================
async def get_db():
    # تأكدي من ضبط DATABASE_URL في تيرموكس عبر أمر export
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    return conn

async def get_locked(chat_id):
    conn = await get_db()
    await conn.execute("INSERT INTO groups(chat_id, locked) VALUES($1, FALSE) ON CONFLICT (chat_id) DO NOTHING", chat_id)
    row = await conn.fetchrow("SELECT locked FROM groups WHERE chat_id=$1", chat_id)
    await conn.close()
    return row['locked'] if row else False

async def build(chat_id):
    conn = await get_db()
    locked = await get_locked(chat_id)
    data = await conn.fetch("SELECT name,status,read_status FROM users WHERE chat_id=$1 ORDER BY created_at ASC", chat_id)
    await conn.close()
    
    status_text = "🔒 التسجيل مغلق" if locked else "🔓 التسجيل مفتوح"
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def section(status):
        result = [f"{row['name']}{' ✅' if row['read_status'] else ''}" for row in data if row['status'] == status]
        return "\n".join(f"{i+1}- {x}" for i, x in enumerate(result)) if result else "لا يوجد"

    return (
        "السلام عليكم ورحمة الله وبركاته\n"
        f"📅 {date_str}\n\n"
        "خادم القرآن الرقمي 💫\n"
        f"{status_text}\n"
        "قائمة تسجيل الأدوار 📝\n\n"
        f"✍️ المسجلات:\n{section('register')}\n\n"
        f"⛔️ المعتذرات:\n{section('excused')}\n\n"
        f"🎧 المستمعات:\n{section('listener')}\n\n"
        f"🚫 المحظورات:\n{section('banned')}\n\n"
        "وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ۚ وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ"
    )

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ قرأت", callback_data="read"), InlineKeyboardButton("✍️ سجل اسمي", callback_data="register")],
        [InlineKeyboardButton("🎧 مستمعة", callback_data="listener"), InlineKeyboardButton("⛔️ معتذرة", callback_data="excused")],
        [InlineKeyboardButton("🔒 قفل/فتح", callback_data="lock"), InlineKeyboardButton("❌ حذف اسمي", callback_data="remove")],
        [InlineKeyboardButton("🧹 تصفير القائمة", callback_data="reset")]
    ])

# =========================
# HANDLERS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    text = await build(update.effective_chat.id)
    await update.message.reply_text(text, reply_markup=menu())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 **تعليمات استخدام خادم القرآن الرقمي**\n\n"
        "✨ **للعضوات:**\n"
        "• استخدمي الأزرار أسفل الرسالة لتسجيل دورك:\n"
        "  - ✅ **قرأت**: لتأكيد القراءة.\n"
        "  - ✍️ **سجل اسمي**: لإضافة اسمك في قائمة المسجلات.\n"
        "  - 🎧 **مستمعة**: إذا كنتِ ستستمعين فقط.\n"
        "  - ⛔️ **معتذرة**: إذا كنتِ لا تستطيعين المشاركة اليوم.\n"
        "  - ❌ **حذف اسمي**: لإزالة اسمك من القوائم.\n\n"
        "👑 **للمشرفات فقط:**\n"
        "• **تشغيل البوت**: `/start`\n"
        "• **القفل/الفتح**: من زر (🔒 قفل/فتح) في القائمة.\n"
        "• **تصفير القائمة**: من زر (🧹 تصفير القائمة) لحذف جميع الأسماء.\n"
        "• **حظر عضوة**: بالرد على رسالة العضوة في المجموعة بالأمر: `/ban`\n"
        "• **فك حظر عضوة**: بالرد على رسالة العضوة في المجموعة بالأمر: `/unban`"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        conn = await get_db()
        await conn.execute(
            "INSERT INTO users (chat_id, user_id, name, status, read_status, created_at) VALUES ($1,$2,$3,'banned',FALSE,$4) ON CONFLICT (chat_id,user_id) DO UPDATE SET status='banned', created_at=$4",
            update.effective_chat.id, target.id, target.full_name, datetime.now()
        )
        await conn.close()
        await update.message.reply_text(f"تم حظر {target.full_name}")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        conn = await get_db()
        await conn.execute("DELETE FROM users WHERE chat_id=$1 AND user_id=$2", update.effective_chat.id, target.id)
        await conn.close()
        await update.message.reply_text(f"تم فك الحظر عن {target.full_name}")

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = q.message.chat_id
    user_id = q.from_user.id
    action = q.data
    conn = await get_db()
    
    status_row = await conn.fetchrow("SELECT status FROM users WHERE chat_id=$1 AND user_id=$2", chat_id, user_id)
    if status_row and status_row['status'] == 'banned':
        await conn.close()
        return

    if action in ["register", "listener", "excused"]:
        if await get_locked(chat_id):
            await conn.close()
            return
        await conn.execute(
            "INSERT INTO users (chat_id,user_id,name,status,read_status,created_at) VALUES ($1,$2,$3,$4,FALSE,$5) ON CONFLICT (chat_id,user_id) DO UPDATE SET status=$4, created_at=$5",
            chat_id, user_id, q.from_user.full_name, action, datetime.now()
        )
    elif action == "read":
        await conn.execute("UPDATE users SET read_status = NOT read_status WHERE chat_id=$1 AND user_id=$2", chat_id, user_id)
    elif action == "remove":
        await conn.execute("DELETE FROM users WHERE chat_id=$1 AND user_id=$2", chat_id, user_id)
    elif action == "lock":
        if await is_admin(update, context):
            await conn.execute("UPDATE groups SET locked = NOT locked WHERE chat_id=$1", chat_id)
    elif action == "reset":
        if await is_admin(update, context):
            await conn.execute("DELETE FROM users WHERE chat_id=$1 AND status!='banned'", chat_id)
    
    new_text = await build(chat_id)
    await conn.close()
    try: await q.edit_message_text(text=new_text, reply_markup=menu())
    except: pass

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("help", help_command))
bot_app.add_handler(CommandHandler("ban", ban_user))
bot_app.add_handler(CommandHandler("unban", unban_user))
bot_app.add_handler(CallbackQueryHandler(buttons))

# =========================
# RUNNING
# =========================
if __name__ == "__main__":
    print("البوت يعمل الآن بنظام Polling...")
    bot_app.run_polling()
