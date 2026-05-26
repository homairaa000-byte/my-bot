import os
import datetime
import pytz
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
users = {} 
registered, readers, listeners, excused, blocked = set(), set(), set(), set()
registration_open = True

def now():
    tz = pytz.timezone("Asia/Riyadh")
    return datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M")

def build_text():
    status = "🔓 التسجيل مفتوح" if registration_open else "🔒 التسجيل مغلق"
    # تنسيق المسجلات
    reg_list = []
    for uid in registered:
        name = users.get(uid, 'عضوة')
        status_icon = " ✅" if uid in readers else ""
        reg_list.append(f"• {name}{status_icon}")
    
    return (
        "خادم القرآن الرقمي 💫\n"
        f"📅 {now()}\n\n{status}\n\n📌 قائمة تسجيل الأدوار\n\n"
        "✍️ المسجلات:\n" + ("\n".join(reg_list) if reg_list else "لا يوجد") + "\n\n"
        "🎧 المستمعات:\n" + ("\n".join(f"• {users.get(uid, 'عضوة')}" for uid in listeners) or "لا يوجد") + "\n\n"
        "⛔️ المعتذرات:\n" + ("\n".join(f"• {users.get(uid, 'عضوة')}" for uid in excused) or "لا يوجد") + "\n\n"
        "🚫 المحظورات:\n" + ("\n".join(f"• {users.get(uid, 'عضوة')}" for uid in blocked) or "لا يوجد") + "\n"
    )

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("سجل اسمي 📝", callback_data="reg"), InlineKeyboardButton("قرأت ✅", callback_data="read")],
        [InlineKeyboardButton("🎧 مستمعة", callback_data="listen"), InlineKeyboardButton("⛔ معتذرة", callback_data="excused")],
        [InlineKeyboardButton("قفل/فتح 🔒", callback_data="toggle"), InlineKeyboardButton("تصفير 🧹", callback_data="reset")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(build_text(), reply_markup=menu())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global registration_open
    q = update.callback_query
    uid, name = q.from_user.id, q.from_user.first_name
    
    if uid in blocked and q.data != "start": await q.answer("🚫 أنتِ محظورة"); return
    
    if q.data == "toggle": registration_open = not registration_open
    elif q.data == "reset": registered.clear(); readers.clear(); listeners.clear(); excused.clear()
    elif q.data == "reg": users[uid] = name; registered.add(uid); listeners.discard(uid); excused.discard(uid)
    elif q.data == "read": readers.add(uid)
    elif q.data == "listen": listeners.add(uid); registered.discard(uid); readers.discard(uid); excused.discard(uid)
    elif q.data == "excused": excused.add(uid); registered.discard(uid); readers.discard(uid); listeners.discard(uid)
    
    await q.answer()
    await q.edit_message_text(build_text(), reply_markup=menu())

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        blocked.add(target.id)
        await update.message.reply_text(f"تم حظر {target.first_name}")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CallbackQueryHandler(buttons))
    print("BOT RUNNING ✔")
    app.run_polling(drop_pending_updates=True)
