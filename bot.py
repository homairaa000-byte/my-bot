import os
import datetime
import pytz
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# إعداد السجلات
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN: 
    raise Exception("BOT_TOKEN غير موجود في متغيرات البيئة!")

# البيانات الأساسية
users = {} 
registered, readers, listeners, excused, blocked = set(), set(), set(), set(), set()
registration_open = True

def now():
    tz = pytz.timezone("Asia/Riyadh")
    return datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M")

def build_text():
    status = "🔓 التسجيل مفتوح" if registration_open else "🔒 التسجيل مغلق"
    reg_names = [f"{i+1} - {users.get(uid, 'غير معروف')}{' ✅' if uid in readers else ''}" for i, uid in enumerate(registered)]
    return (
        "خادم القرآن الرقمي 💫\n"
        f"📅 {now()}\n\n{status}\n\n📌 قائمة تسجيل الأدوار\n\n"
        "✍️ المسجلات:\n" + ("\n".join(reg_names) or "لا يوجد") + "\n\n"
        "🎧 المستمعات:\n" + ("\n".join(users.get(uid, "") for uid in listeners) or "لا يوجد") + "\n\n"
        "⛔️ المعتذرات:\n" + ("\n".join(users.get(uid, "") for uid in excused) or "لا يوجد") + "\n"
    )

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("سجل اسمي 📝", callback_data="reg"), InlineKeyboardButton("قرأت ✅", callback_data="read")],
        [InlineKeyboardButton("🎧 مستمعة", callback_data="listen"), InlineKeyboardButton("⛔ معتذرة", callback_data="excused")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(build_text(), reply_markup=menu())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global registration_open
    q = update.callback_query
    await q.answer()
    uid, name = q.from_user.id, q.from_user.first_name
    
    if uid in blocked: return
    if not registration_open: 
        await q.answer("🔒 التسجيل مغلق", show_alert=True)
        return
        
    if q.data == "reg": users[uid] = name; registered.add(uid)
    elif q.data == "read" and uid in registered: readers.add(uid)
    elif q.data == "listen": listeners.add(uid); registered.discard(uid); readers.discard(uid); excused.discard(uid)
    elif q.data == "excused": excused.add(uid); registered.discard(uid); readers.discard(uid); listeners.discard(uid)
    
    await q.edit_message_text(build_text(), reply_markup=menu())

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        blocked.add(target.id)
        await update.message.reply_text("تم الحظر")

if __name__ == '__main__':
    # بناء التطبيق
    app = Application.builder().token(TOKEN).concurrent_updates(False).build()
    
    # إضافة الأوامر
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CallbackQueryHandler(buttons))
    
    print("BOT RUNNING ✔")
    
    # drop_pending_updates=True هي المفتاح لمسح التعارض مع أي اتصالات قديمة
    app.run_polling(drop_pending_updates=True)
