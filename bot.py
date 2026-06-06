import os
import asyncio
import aiosqlite
import threading
from datetime import datetime
import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# =========================
# SETTINGS
# =========================
TOKEN = os.getenv("BOT_TOKEN")
DB = "bot.db"
WEBHOOK_URL = "https://my-bot-nquv.onrender.com/webhook"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

bot_app = Application.builder().token(TOKEN).build()
flask_app = Flask(__name__)

main_loop = None

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
    conn = await aiosqlite.connect(DB)
    await conn.execute("PRAGMA journal_mode=WAL;")
    await conn.execute("CREATE TABLE IF NOT EXISTS groups (chat_id INTEGER PRIMARY KEY, locked INTEGER DEFAULT 0)")
    # إضافة عمود created_at لتسجيل وقت الانضمام لكل حالة
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER, 
            user_id INTEGER, 
            name TEXT, 
            status TEXT, 
            read_status INTEGER DEFAULT 0, 
            created_at TIMESTAMP,
            PRIMARY KEY(chat_id, user_id)
        )
    """)
    await conn.commit()
    return conn

async def get_locked(chat_id):
    conn = await get_db()
    await conn.execute("INSERT OR IGNORE INTO groups(chat_id, locked) VALUES (?,0)", (chat_id,))
    await conn.commit()
    async with conn.execute("SELECT locked FROM groups WHERE chat_id=?", (chat_id,)) as c:
        row = await c.fetchone()
    await conn.close()
    return row[0] if row else 0

async def build(chat_id):
    conn = await get_db()
    locked = await get_locked(chat_id)
    # جلب البيانات مرتبة حسب وقت التسجيل (الأقدم أولاً)
    async with conn.execute("SELECT name,status,read_status FROM users WHERE chat_id=? ORDER BY created_at ASC", (chat_id,)) as c:
        data = await c.fetchall()
    await conn.close()
    
    status_text = "🔒 التسجيل مغلق" if locked else "🔓 التسجيل مفتوح"
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def section(status):
        result = [f"{name}{' ✅' if r == 1 else ''}" for name, s, r in data if s == status]
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
        # إضافة التاريخ عند الحظر لترتيب المحظورات
        await conn.execute("INSERT OR REPLACE INTO users (chat_id, user_id, name, status, read_status, created_at) VALUES (?, ?, ?, 'banned', 0, ?)", 
                           (update.effective_chat.id, target.id, target.full_name, datetime.now()))
        await conn.commit()
        await conn.close()
        await update.message.reply_text(f"تم حظر {target.full_name}")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        conn = await get_db()
        await conn.execute("DELETE FROM users WHERE chat_id=? AND user_id=?", (update.effective_chat.id, target.id))
        await conn.commit()
        await conn.close()
        await update.message.reply_text(f"تم فك الحظر عن {target.full_name}")

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = q.message.chat_id
    user_id = q.from_user.id
    action = q.data
    conn = await get_db()
    
    async with conn.execute("SELECT status FROM users WHERE chat_id=? AND user_id=?", (chat_id, user_id)) as c:
        status_row = await c.fetchone()
    
    if status_row and status_row[0] == 'banned':
        await conn.close()
        return

    # عند اختيار حالة، يتم تحديث الوقت الحالي لضمان الترتيب التلقائي في القائمة
    if action in ["register", "listener", "excused"]:
        if await get_locked(chat_id):
            await conn.close()
            return
        await conn.execute("INSERT OR REPLACE INTO users (chat_id, user_id, name, status, read_status, created_at) VALUES (?, ?, ?, ?, 0, ?)", 
                           (chat_id, user_id, q.from_user.full_name, action, datetime.now()))
    elif action == "read":
        await conn.execute("UPDATE users SET read_status = CASE WHEN read_status=1 THEN 0 ELSE 1 END WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    elif action == "remove":
        await conn.execute("DELETE FROM users WHERE chat_id=? AND user_id=?", (chat_id, user_id))
    elif action == "lock":
        if await is_admin(update, context):
            await conn.execute("UPDATE groups SET locked = CASE WHEN locked=1 THEN 0 ELSE 1 END WHERE chat_id=?", (chat_id,))
    elif action == "reset":
        if await is_admin(update, context):
            await conn.execute("DELETE FROM users WHERE chat_id=? AND status != 'banned'", (chat_id,))
    
    await conn.commit()
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
# WEBHOOK & RUN
# =========================
@flask_app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot_app.bot)
    asyncio.run_coroutine_threadsafe(bot_app.process_update(update), main_loop)
    return "ok", 200

async def run_bot():
    global main_loop
    main_loop = asyncio.get_running_loop()
    await bot_app.initialize()
    await bot_app.bot.set_webhook(WEBHOOK_URL)
    def run_flask():
        flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), use_reloader=False)
    threading.Thread(target=run_flask, daemon=True).start()
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(run_bot())

