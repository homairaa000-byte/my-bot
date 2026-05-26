import os
import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN: raise Exception("BOT_TOKEN missing")

users = {} 
registered, readers, listeners, excused, blocked = set(), set(), set(), set(), set()
registration_open = True

def now():
    tz = pytz.timezone("Asia/Riyadh")
    return datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M")

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
        return member.status in ["administrator", "creator"]
    except: return False

def build_text():
    status = "🔓 التسجيل مفتوح" if registration_open else "🔒 التسجيل مغلق"
    reg_names = [f"{i+1} - {users.get(uid, 'غير معروف')}{' ✅' if uid in readers else ''}" for i, uid in enumerate(registered)]
    return (
        "🌿 أهلاً بكِ يا هميراء في خادم القرآن الرقمي 💫\n"
        f"📅 {now()}\n\n{status}\n\n📌 قائمة تسجيل الأدوار\n\n"
        "✍️ المسجلات:\n" + ("\n".join(reg_names) or "لا يوجد") + "\n\n"
        "🎧 المستمعات:\n" + ("\n".join(users.get(uid, "") for uid in listeners) or "لا يوجد") + "\n\n"
        "⛔️ المعتذرات:\n" + ("\n".join(users.get(uid, "") for uid in excused) or "لا يوجد") + "\n\n"
        "🚫 المحظورات:\n" + ("\n".join(blocked) or "لا يوجد") + "\n"
    )

def menu(is_admin_user=False):
    # ترتيب الأزرار الجديد: سجل يمين، قرأت يسار
    buttons = [
        [InlineKeyboardButton("سجل اسمي 📝", callback_data="reg"), InlineKeyboardButton("قرأت ✅", callback_data="read")],
        [InlineKeyboardButton("🎧 مستمعة", callback_data="listen"), InlineKeyboardButton("⛔ معتذرة", callback_data="excused")]
    ]
    if is_admin_user:
        buttons.append([InlineKeyboardButton("🔒 قفل/فتح", callback_data="toggle"), InlineKeyboardButton("🧹 تصفير", callback_data="reset")])
        buttons.append([InlineKeyboardButton("♻️ إلغاء الحظر", callback_data="unban")])
    return InlineKeyboardMarkup(buttons)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin = await is_admin(update, context, update.effective_user.id)
    if update.effective_chat.type == "private":
        await update.message.reply_text("🌿 أهلاً بكِ يا هميراء في خادم القرآن الرقمي 💫")
    await update.message.reply_text(build_text(), reply_markup=menu(admin))

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global registration_open
    q = update.callback_query
    await q.answer()
    uid, name = q.from_user.id, q.from_user.first_name
    admin = await is_admin(update, context, uid)

    if q.data in ["toggle", "reset", "unban"]:
        if not admin: return
        if q.data == "toggle": registration_open = not registration_open
        elif q.data == "reset": users.clear(); registered.clear(); readers.clear(); listeners.clear(); excused.clear(); blocked.clear()
        elif q.data == "unban" and blocked: blocked.pop(next(iter(blocked)))
        await q.edit_message_text(build_text(), reply_markup=menu(admin))
        return

    if not registration_open: await q.answer("🔒 التسجيل مغلق", show_alert=True); return
    if q.data == "reg": users[uid] = name; registered.add(uid)
    elif q.data == "read" and uid in registered: readers.add(uid)
    elif q.data == "listen": listeners.add(uid); registered.discard(uid); readers.discard(uid); excused.discard(uid)
    elif q.data == "excused": excused.add(uid); registered.discard(uid); readers.discard(uid); listeners.discard(uid)
    await q.edit_message_text(build_text(), reply_markup=menu(admin))

async def block_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context, update.message.from_user.id) and any(x in (update.message.text or "").lower() for x in ["http", "www", "t.me"]):
        try: await update.message.delete()
        except: pass
        await update.message.reply_text("🚫 تنبيه: يمنع إرسال الروابط")

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, block_links))
app.run_polling(drop_pending_updates=True)
