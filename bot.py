import os
import re
import datetime
import pytz
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# جلب التوكين من المتغيرات في Railway
TOKEN = os.getenv("BOT_TOKEN")

users = {}
registered, readers, listeners, excused, blocked = set(), set(), set(), set(), set()
registration_open = False

async def is_admin(update, context):
    """دالة عامة تتحقق من صلاحيات أي مشرفة في المجموعة"""
    try:
        user = update.effective_user
        chat_id = update.effective_chat.id
        # جلب قائمة المشرفين الحقيقية من تيليجرام
        admins = await context.bot.get_chat_administrators(chat_id)
        # إذا كان المستخدم ضمن قائمة المشرفين، نرجع True
        return any(admin.user.id == user.id for admin in admins)
    except:
        return False

def build_text():
    status = "🔓 التسجيل مفتوح" if registration_open else "🔒 التسجيل مغلق"
    def fmt(s): return "\n".join([f"{i}- {users.get(uid, 'عضوة')}" for i, uid in enumerate(s, 1)]) if s else "لا يوجد"
    return (
        "خادم القرآن الرقمي 💫\n"
        f"📅 {datetime.datetime.now(pytz.timezone('Asia/Riyadh')).strftime('%Y-%m-%d %H:%M')}\n\n{status}\n\n"
        "✍️ المسجلات:\n" + ("\n".join([f"{i}- {users.get(uid, 'عضوة')}{' ✅' if uid in readers else ''}" for i, uid in enumerate(registered, 1)])) + "\n\n"
        "🎧 المستمعات:\n" + fmt(listeners) + "\n\n"
        "⛔️ المعتذرات:\n" + fmt(excused) + "\n\n"
        "🚫 المحظورات:\n" + fmt
