import os
import re
import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
# ضعي هنا أرقام الـ ID الخاصة بالمشرفات (بينهم فواصل)
ADMINS = {123456789, 987654321} 

users = {}
registered, readers, listeners, excused, blocked = set(), set(), set(), set(), set()
registration_open = False

def is_admin(user_id):
    return user_id in ADMINS

def build_text():
    status = "🔓 التسجيل مفتوح" if registration_open else "🔒 التسجيل مغلق"
    def format_list(data_set):
        return "\n".join([f"{i}- {users.get(uid, 'عضوة')}" for i, uid in enumerate(data_set, 1)]) if data_set else "لا يوجد"

    return (
        "خادم القرآن الرقمي 💫\n"
        f"📅 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n{status}\n\n"
        "✍️ المسجلات:\n" + ("\n".join([f"{i}- {users.get(uid, 'عضوة')}{' ✅' if uid in readers else ''}" for i, uid in enumerate(registered, 1)])) + "\n\n"
        "🎧 المستمعات:\n" + format_list(listeners) + "\n\n"
        "⛔️ المعتذرات:\n" + format_list(excused) + "\n\n"
        "🚫 المحظورات:\n" + format_list(blocked) + "\n\n"
        "{ وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا }\n"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # أمر القائمة متاح للجميع للعرض، ولكن التحكم فيه للمشرفات فقط
    await update.message.reply_text(build_text(), reply_markup=menu())

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("قرأت ✅", callback_data="read"), InlineKeyboardButton("سجل اسمي 📝", callback_data="reg")],
        [InlineKeyboardButton("🎧 مستمعة", callback_data="listen"), InlineKeyboardButton("⛔ معتذرة", callback_data="excused")],
        [InlineKeyboardButton("قفل/فتح 🔒", callback_data="toggle"), InlineKeyboardButton("تصفير 🧹", callback_data="reset")]
    ])

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    
    if uid in blocked: return
    
    # حصر أوامر التحكم بالمشرفات فقط
    if q.data in ["toggle", "reset"]:
        if not is_admin(uid):
            await q.answer("🚫 هذا الأمر للمشرفات فقط!", show_alert=True)
            return
        if q.data == "toggle": global registration_open; registration_open = not registration_open
        elif q.data == "reset": registered.clear(); readers.clear(); listeners.clear(); excused.clear()
    
    # الأوامر العامة
    elif q.data == "reg": users[uid] = q.from_user.first_name; registered.add(uid); listeners.discard(uid); excused.discard(uid)
    elif q.data == "read": readers.add(uid)
    elif q.data == "listen": listeners.add(uid); registered.discard(uid); readers.discard(uid); excused.discard(uid)
    elif q.data == "excused": excused.add(uid); registered.discard(uid); readers.discard(uid); listeners.discard(uid)
    
    await q.edit_message_text(build_text(), reply_markup=menu())

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.message.from_user.id): return
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        blocked.add(target.id)
        users[target.id] = target.first_name
        await update.message.reply_text(f"تم حظر {target.first_name} وإضافتها للمحظورات.")

async def handle_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.message.from_user.id) and re.search(r'http[s]?://', update.message.text or ""):
        await update.message.delete()
        await update.message.reply_text(f"🚫🚫 تنبيه {update.message.from_user.first_name}...\nإرسال روابط من دون إذن المشرفات يعرضك للحذف أو الحظر")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_links))
    app.add_handler(CallbackQueryHandler(buttons))
    app.run_polling()
