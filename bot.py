import os
import re
import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
# ضعي هنا أرقام الـ ID للمشرفات (أرقام فقط)
ADMINS = {123456789, 987654321} 

users = {}
registered, readers, listeners, excused, blocked = set(), set(), set(), set(), set()
registration_open = False

def is_admin(user_id): return user_id in ADMINS

def build_text():
    status = "🔓 التسجيل مفتوح" if registration_open else "🔒 التسجيل مغلق"
    def fmt(s): return "\n".join([f"{i}- {users.get(uid, 'عضوة')}" for i, uid in enumerate(s, 1)]) if s else "لا يوجد"
    
    return (
        "خادم القرآن الرقمي 💫\n"
        f"📅 {datetime.datetime.now(pytz.timezone('Asia/Riyadh')).strftime('%Y-%m-%d %H:%M')}\n\n{status}\n\n"
        "✍️ المسجلات:\n" + ("\n".join([f"{i}- {users.get(uid, 'عضوة')}{' ✅' if uid in readers else ''}" for i, uid in enumerate(registered, 1)])) + "\n\n"
        "🎧 المستمعات:\n" + fmt(listeners) + "\n\n"
        "⛔️ المعتذرات:\n" + fmt(excused) + "\n\n"
        "🚫 المحظورات:\n" + fmt(blocked) + "\n\n"
        "{ وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا }\n"
    )

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("قرأت ✅", callback_data="read"), InlineKeyboardButton("سجل اسمي 📝", callback_data="reg")],
        [InlineKeyboardButton("🎧 مستمعة", callback_data="listen"), InlineKeyboardButton("⛔ معتذرة", callback_data="excused")],
        [InlineKeyboardButton("قفل/فتح 🔒", callback_data="toggle"), InlineKeyboardButton("تصفير 🧹", callback_data="reset")]
    ])

async def start(update, context): await update.message.reply_text(build_text(), reply_markup=menu())

async def buttons(update, context):
    q = update.callback_query
    uid, name = q.from_user.id, q.from_user.first_name
    if uid in blocked: return
    
    if q.data in ["toggle", "reset"]:
        if not is_admin(uid): await q.answer("🚫 للمشرفات فقط!", show_alert=True); return
        global registration_open
        if q.data == "toggle": registration_open = not registration_open
        else: registered.clear(); readers.clear(); listeners.clear(); excused.clear()
    else:
        if q.data == "reg": users[uid] = name; registered.add(uid); listeners.discard(uid); excused.discard(uid)
        elif q.data == "read": readers.add(uid)
        elif q.data == "listen": listeners.add(uid); registered.discard(uid); readers.discard(uid); excused.discard(uid)
        elif q.data == "excused": excused.add(uid); registered.discard(uid); readers.discard(uid); listeners.discard(uid)
    
    await q.edit_message_text(build_text(), reply_markup=menu())

async def ban_user(update, context):
    if is_admin(update.message.from_user.id) and update.message.reply_to_message:
        t = update.message.reply_to_message.from_user
        blocked.add(t.id); users[t.id] = t.first_name
        await update.message.reply_text(f"تم حظر {t.first_name}")

async def handle_links(update, context):
    if not is_admin(update.message.from_user.id) and re.search(r'http[s]?://', update.message.text or ""):
        await update.message.delete()
        await update.message.reply_text(f"🚫 تنبيه: إرسال الروابط ممنوع!")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_links))
    app.add_handler(CallbackQueryHandler(buttons))
    app.run_polling(drop_pending_updates=True)
