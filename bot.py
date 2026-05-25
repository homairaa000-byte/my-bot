import os
import datetime
import pytz

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# =========================
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise Exception("BOT_TOKEN missing")

# =========================
DATA
# =========================
registered = {}
readers = set()
listeners = set()
excused = set()
blocked = {}
registration_open = True

# =========================
TIME
# =========================
def now():
    tz = pytz.timezone("Asia/Riyadh")
    return datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M")

# =========================
ADMIN CHECK
# =========================
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
        return member.status in ['administrator', 'creator']
    except:
        return False

# =========================
TEXT BUILD
# =========================
def build_text():
    status = "🔓 التسجيل مفتوح" if registration_open else "🔒 التسجيل مغلق"
    return (
        "السلام عليكم ورحمة الله وبركاته 🌿\n\n"
        "خادم القرآن الرقمي 🤍\n"
        f"📅 {now()}\n\n"
        f"{status}\n\n"
        "📌 قائمة تسجيل الأدوار\n\n"
        "✍️ المسجلات:\n" + ("\n".join([f"• {n}" for n in registered.values()]) or "لا يوجد") + "\n\n"
        "🎧 المستمعات:\n" + ("\n".join(listeners) or "لا يوجد") + "\n\n"
        "⛔️ المعتذرات:\n" + ("\n".join(excused) or "لا يوجد") + "\n\n"
        "🚫 المحظورات:\n" + ("\n".join(blocked.values()) or "لا يوجد") + "\n\n"
        "﴿ وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ﴾"
    )

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ سجل", callback_data="reg"), InlineKeyboardButton("📖 قرأت", callback_data="read")],
        [InlineKeyboardButton("🎧 مستمعة", callback_data="listen"), InlineKeyboardButton("⛔ معتذرة", callback_data="excused")],
        [InlineKeyboardButton("🔒 قفل/فتح", callback_data="toggle"), InlineKeyboardButton("🧹 تصفير", callback_data="reset")]
    ])

# =========================
HANDLERS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # إرسال الترحيب في الخاص فقط
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "🌿 أهلاً بك في خادم القرآن الرقمي 🤍\n\n"
            "📌 وظائف البوت:\n"
            "• تنظيم تسجيل الأدوار\n"
            "• متابعة القراءة\n"
            "• تنظيم المستمعات والمعتذرات\n"
            "• إدارة المحظورات\n\n"
            "🤍 اللهم اجعل أعمالنا خالصة لوجهك الكريم"
        )
        await update.message.reply_text(build_text(), reply_markup=menu())
    # في المجموعات يمكننا إرسال القائمة فقط إذا رغبتِ (اختياري)
    elif update.effective_chat.type in ["group", "supergroup"]:
        await update.message.reply_text(build_text(), reply_markup=menu())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global registration_open
    q = update.callback_query
    await q.answer()
    
    uid = q.from_user.id
    name = q.from_user.first_name

    if uid in blocked:
        await q.answer("🚫 أنتِ محظورة", show_alert=True)
        return

    # التحقق من صلاحيات الأزرار الإدارية
    if q.data in ["toggle", "reset"]:
        if not await is_admin(update, context, uid):
            await q.answer("🚫 هذه الصلاحية للمشرفات فقط", show_alert=True)
            return
        if q.data == "toggle": registration_open = not registration_open
        elif q.data == "reset":
            registered.clear(); readers.clear(); listeners.clear(); excused.clear()
    
    # العمليات العادية
    elif registration_open:
        if q.data == "reg": registered[uid] = name
        elif q.data == "read" and uid in registered: readers.add(name)
        elif q.data == "listen": listeners.add(name); registered.pop(uid, None)
        elif q.data == "excused": excused.add(name); registered.pop(uid, None)
    else:
        await q.answer("🔒 التسجيل مغلق", show_alert=True)
        return

    await q.edit_message_text(build_text(), reply_markup=menu())

async def block_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_admin(update, context, update.message.from_user.id): return
    if "http" in (update.message.text or "").lower() or "www" in (update.message.text or "").lower():
        await update.message.delete()
        await update.message.reply_text("🚫🚫🚫 إرسال رابط من غير إذن الإشراف يعرضك للحذف أو الحظر")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context, update.message.from_user.id): return
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        blocked[user.id] = user.first_name
        registered.pop(user.id, None)
        await update.message.reply_text(f"🚫 تم حظر {user.first_name}")

# =========================
APP
# =========================
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ban", ban))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, block_links))

print("BOT RUNNING ✔")
app.run_polling(drop_pending_updates=True)
