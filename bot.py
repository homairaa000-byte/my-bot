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
        "خادم القرآن الرقمي 💫\n"
        f"📅 {now()}\n\n{status}\n\n📌 قائمة تسجيل الأدوار\n\n"
        "✍️ المسجلات:\n" + ("\n".join(reg_names) or "لا يوجد") + "\n\n"
        "🎧 المستمعات:\n" + ("\n".join(users.get(uid, "") for uid in listeners) or "لا يوجد") + "\n\n"
        "⛔️ المعتذرات:\n" + ("\n".join(users.get(uid, "") for uid in excused) or "لا يوجد") + "\n\n"
        "🚫 المحظورات:\n" + ("\n".join(users.get(uid, "") for uid in blocked) or "لا يوجد") + "\n"
    )

def menu():
    # الأزرار مرتبة كما طلبتِ
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("سجل اسمي 📝", callback_data="reg"), InlineKeyboardButton("قرأت ✅", callback_data="read")],
        [InlineKeyboardButton("🎧 مستمعة", callback_data="listen"), InlineKeyboardButton("⛔ معتذرة", callback_data="excused")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text("خادم القرآن الرقمي 💫")
    await update.message.reply_text(build_text(), reply_markup=menu())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global registration_open
    q = update.callback_query
    await q.answer()
    uid, name = q.from_user.id, q.from_user.first_name
    
    if uid in blocked: return
    if not registration_open: await q.answer("🔒 التسجيل مغلق", show_alert=True); return
    
    if q.data == "reg": users[uid] = name; registered.add(uid)
    elif q.data == "read" and uid in registered: readers.add(uid)
    elif q.data == "listen": listeners.add(uid); registered.discard(uid); readers.discard(uid); excused.discard(uid)
    elif q.data == "excused": excused.add(uid); registered.discard(uid); readers.discard(uid); listeners.discard(uid)
    
    await q.edit_message_text(build_text(), reply_markup=menu())

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context, update.message.from_user.id): return
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        blocked.add(target.id)
        users.pop(target.id, None); registered.discard(target.id); readers.discard(target.id); listeners.discard(target.id); excused.discard(target.id)
        await update.message.reply_text(build_text(), reply_markup=menu())

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context, update.message.from_user.id): return
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        blocked.discard(target.id)
        await update.message.reply_text(build_text(), reply_markup=menu())

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ban", ban))
app.add_handler(CommandHandler("unban", unban))
app.add_handler(CallbackQueryHandler(buttons))
app.run_polling(drop_pending_updates=True)
