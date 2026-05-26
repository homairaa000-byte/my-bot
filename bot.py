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
# DATA
# =========================
users = {}  # uid -> name

registered = set()
readers = set()
listeners = set()
excused = set()
blocked = set()

registration_open = True

# =========================
def now():
    tz = pytz.timezone("Asia/Riyadh")
    return datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M")

# =========================
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False

# =========================
def build_text():
    status = "🔓 التسجيل مفتوح" if registration_open else "🔒 التسجيل مغلق"
    registered_names = []
    seen = set()

    for uid in registered:
        name = users.get(uid, "غير معروف")
        if name in seen:
            continue
        seen.add(name)
        if uid in readers:
            registered_names.append(f"{len(registered_names)+1} - {name} ✅")
        else:
            registered_names.append(f"{len(registered_names)+1} - {name}")

    listeners_text = "\n".join(users.get(uid, "") for uid in listeners) or "لا يوجد"
    excused_text = "\n".join(users.get(uid, "") for uid in excused) or "لا يوجد"
    blocked_text = "\n".join(blocked) or "لا يوجد" # تم تعديلها لتناسب القائمة

    return (
        "🌿 أهلاً بكِ يا هميراء في خادم القرآن الرقمي 💫\n"
        f"📅 {now()}\n\n"
        f"{status}\n\n"
        "📌 قائمة تسجيل الأدوار\n\n"
        "✍️ المسجلات:\n" + ("\n".join(registered_names) or "لا يوجد") + "\n\n"
        "🎧 المستمعات:\n" + listeners_text + "\n\n"
        "⛔️ المعتذرات:\n" + excused_text + "\n\n"
        "🚫 المحظورات:\n" + blocked_text + "\n\n"
    )

# =========================
def menu():
    # تعديل ترتيب الأزرار وتغيير الأيقونات
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("سجل اسمي 📝", callback_data="reg"),
            InlineKeyboardButton("قرأت ✅", callback_data="read")
        ],
        [
            InlineKeyboardButton("🎧 مستمعة", callback_data="listen"),
            InlineKeyboardButton("⛔ معتذرة", callback_data="excused")
        ],
        [
            InlineKeyboardButton("🔒 قفل/فتح", callback_data="toggle"),
            InlineKeyboardButton("🧹 تصفير", callback_data="reset")
        ],
        [
            InlineKeyboardButton("♻️ إلغاء الحظر", callback_data="unban")
        ]
    ])

# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # إرسال ترحيب فقط إذا كان في الخاص
    if update.effective_chat.type == "private":
        await update.message.reply_text("🌿 أهلاً بكِ يا هميراء في خادم القرآن الرقمي 💫\nاختر من الأزرار 👇")
    
    # إرسال القائمة في كل الحالات
    await update.message.reply_text(build_text(), reply_markup=menu())

# =========================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global registration_open
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    name = q.from_user.first_name

    if uid in blocked:
        await q.answer("🚫 أنتِ محظورة", show_alert=True)
        return

    if q.data in ["toggle", "reset", "unban"]:
        if not await is_admin(update, context, uid):
            await q.answer("🚫 للمشرفات فقط", show_alert=True)
            return
        if q.data == "toggle":
            registration_open = not registration_open
        elif q.data == "reset":
            users.clear(); registered.clear(); readers.clear(); listeners.clear(); excused.clear(); blocked.clear()
        elif q.data == "unban":
            if blocked: blocked.pop(next(iter(blocked)))
        await q.edit_message_text(build_text(), reply_markup=menu())
        return

    if not registration_open:
        await q.answer("🔒 التسجيل مغلق", show_alert=True)
        return

    if q.data == "reg":
        users[uid] = name
        registered.add(uid)
    elif q.data == "read":
        if uid in registered: readers.add(uid)
    elif q.data == "listen":
        listeners.add(uid); registered.discard(uid); readers.discard(uid); excused.discard(uid)
    elif q.data == "excused":
        excused.add(uid); registered.discard(uid); readers.discard(uid); listeners.discard(uid)

    await q.edit_message_text(build_text(), reply_markup=menu())

# =========================
async def block_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_admin(update, context, update.message.from_user.id): return
    text = (update.message.text or "").lower()
    if "http" in text or "www" in text or "t.me" in text:
        try: await update.message.delete()
        except: pass
        await update.message.reply_text("🚫 تنبيه ... إرسال روابط من دون إذن المشرفات يعرضك للحذف أو الحظر")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context, update.message.from_user.id): return
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        blocked.add(user.id)
        users.pop(user.id, None); registered.discard(user.id); readers.discard(user.id); listeners.discard(user.id); excused.discard(user.id)
        await update.message.reply_text(build_text(), reply_markup=menu())

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ban", ban))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, block_links))
app.run_polling(drop_pending_updates=True)
