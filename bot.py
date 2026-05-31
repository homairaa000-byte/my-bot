import os
import logging
import asyncio
from datetime import datetime

import pytz
from flask import Flask, request

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# =========================
# الإعدادات
# =========================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TOKEN:
    raise Exception("BOT_TOKEN missing")

if not WEBHOOK_URL:
    raise Exception("WEBHOOK_URL missing")

# =========================
# Flask
# =========================

app = Flask(__name__)

# =========================
# بيانات المجموعات
# =========================

chat_data = {}


def get_data(chat_id):
    if chat_id not in chat_data:
        chat_data[chat_id] = {
            "registered": [],
            "readers": set(),
            "listeners": set(),
            "excused": set(),
            "blocked": set(),          # IDs
            "blocked_names": {},       # id -> name
            "registration_open": True,
        }

    return chat_data[chat_id]


# =========================
# القائمة
# =========================

def menu():
    keyboard = [
        [
            InlineKeyboardButton("✅ قرأت", callback_data="read"),
            InlineKeyboardButton("✍️ سجل اسمي", callback_data="register"),
        ],
        [
            InlineKeyboardButton("🎧 مستمعة", callback_data="listener"),
            InlineKeyboardButton("⛔️ معتذرة", callback_data="excused"),
        ],
        [
            InlineKeyboardButton("🧹 تصفير", callback_data="reset"),
            InlineKeyboardButton("🔒 قفل/فتح", callback_data="toggle"),
        ],
        [
            InlineKeyboardButton("❌ حذف اسمي", callback_data="remove")
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================
# بناء النص
# =========================

def build_text(chat_id):
    data = get_data(chat_id)

    tz = pytz.timezone("Africa/Tripoli")
    date_str = datetime.now(tz).strftime("%Y-%m-%d %H:%M")

    status = "🔓 مفتوح" if data["registration_open"] else "🔒 مغلق"

    def format_list(items, readers_check=False):
        if not items:
            return "لا يوجد"

        result = []

        for i, name in enumerate(items, start=1):
            if readers_check:
                mark = " ✅" if name in data["readers"] else ""
                result.append(f"{i}- {name}{mark}")
            else:
                result.append(f"{i}- {name}")

        return "\n".join(result)

    blocked_names = list(data["blocked_names"].values())

    return (
        "السلام عليكم ورحمة الله وبركاته 🌿\n\n"
        f"📅 {date_str}\n\n"
        "خادم القرآن الرقمي 💫\n\n"
        f"التسجيل {status}\n\n"
        "قائمة تسجيل الأدوار 📝\n\n"
        f"✍️ المسجلات:\n{format_list(data['registered'], True)}\n\n"
        f"⛔️ المعتذرات:\n{format_list(list(data['excused']))}\n\n"
        f"🎧 المستمعات:\n{format_list(list(data['listeners']))}\n\n"
        f"🚫 المحظورات:\n{format_list(blocked_names)}\n\n"
        "﴿ وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ۚ وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ ﴾"
    )


# =========================
# صلاحيات المشرفات
# =========================

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        admins = await context.bot.get_chat_administrators(
            update.effective_chat.id
        )

        return any(
            admin.user.id == update.effective_user.id
            for admin in admins
        )

    except Exception:
        return False


# =========================
# الحظر
# =========================

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await is_admin(update, context):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "يرجى الرد على رسالة العضوة المراد حظرها."
        )
        return

    target = update.message.reply_to_message.from_user

    user_id = target.id
    user_name = target.full_name

    data = get_data(update.effective_chat.id)

    data["blocked"].add(user_id)
    data["blocked_names"][user_id] = user_name

    if user_name in data["registered"]:
        data["registered"].remove(user_name)

    data["readers"].discard(user_name)
    data["listeners"].discard(user_name)
    data["excused"].discard(user_name)

    await update.message.reply_text(
        f"🚫 تم حظر العضوة:\n{user_name}"
    )


# =========================
# الأوامر
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلاً بك في خادم القرآن الرقمي 💫\n\nاستخدم /help للمساعدة."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = (
        "💡 دليل استخدام البوت\n\n"
        "✍️ سجل اسمي\n"
        "إضافة اسمك إلى قائمة المسجلات.\n\n"
        "✅ قرأت\n"
        "تأكيد القراءة.\n\n"
        "🎧 مستمعة\n"
        "نقل اسمك لقائمة المستمعات.\n\n"
        "⛔️ معتذرة\n"
        "نقل اسمك لقائمة المعتذرات.\n\n"
        "❌ حذف اسمي\n"
        "إزالة اسمك من جميع القوائم.\n\n"
        "🔒 للمشرفات فقط:\n"
        "🧹 تصفير\n"
        "🔒 قفل/فتح\n"
        "/ban بالرد على رسالة العضوة."
    )

    await update.message.reply_text(text)


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        build_text(update.effective_chat.id),
        reply_markup=menu(),
    )


# =========================
# الأزرار
# =========================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    chat_id = update.effective_chat.id

    user_name = update.effective_user.full_name
    user_id = update.effective_user.id

    data = get_data(chat_id)

    if user_id in data["blocked"]:
        await query.answer(
            "أنتِ محظورة من استخدام البوت!",
            show_alert=True,
        )
        return

    def remove_user_everywhere(name):

        if name in data["registered"]:
            data["registered"].remove(name)

        data["readers"].discard(name)
        data["listeners"].discard(name)
        data["excused"].discard(name)

    if query.data == "read":

        if user_name not in data["registered"]:
            await query.answer(
                "يجب تسجيل اسمك أولاً!",
                show_alert=True,
            )
            return

        if user_name in data["readers"]:
            data["readers"].remove(user_name)
        else:
            data["readers"].add(user_name)

    elif query.data == "register":

        if not data["registration_open"]:
            await query.answer(
                "التسجيل مغلق حالياً.",
                show_alert=True,
            )
            return

        remove_user_everywhere(user_name)
        data["registered"].append(user_name)

    elif query.data == "listener":

        remove_user_everywhere(user_name)
        data["listeners"].add(user_name)

    elif query.data == "excused":

        remove_user_everywhere(user_name)
        data["excused"].add(user_name)

    elif query.data == "remove":

        remove_user_everywhere(user_name)

    elif query.data in ["toggle", "reset"]:

        if not await is_admin(update, context):
            await query.answer(
                "للمشرفات فقط!",
                show_alert=True,
            )
            return

        if query.data == "toggle":
            data["registration_open"] = (
                not data["registration_open"]
            )

        elif query.data == "reset":
            data["registered"] = []
            data["readers"] = set()
            data["listeners"] = set()
            data["excused"] = set()

    await query.edit_message_text(
        build_text(chat_id),
        reply_markup=menu(),
    )


# =========================
# أوامر تيليجرام
# =========================

async def post_init(application):

    await application.bot.set_my_commands(
        [
            BotCommand("start", "تشغيل البوت"),
            BotCommand("help", "المساعدة"),
            BotCommand("list", "عرض القائمة"),
            BotCommand("ban", "حظر عضوة"),
        ]
    )


application = (
    Application.builder()
    .token(TOKEN)
    .post_init(post_init)
    .build()
)

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("list", list_command))
application.add_handler(CommandHandler("ban", ban_command))
application.add_handler(CallbackQueryHandler(buttons))


# =========================
# Flask Routes
# =========================

@app.route("/")
def home():
    return "Bot is running!"


@app.post(f"/webhook/{TOKEN}")
def telegram_webhook():

    update = Update.de_json(
        request.get_json(force=True),
        application.bot,
    )

    asyncio.run(application.process_update(update))

    return "OK"


# =========================
# تشغيل Webhook
# =========================

async def setup_webhook():

    await application.initialize()

    await application.bot.delete_webhook(
        drop_pending_updates=True
    )

    await application.bot.set_webhook(
        url=f"{WEBHOOK_URL}/webhook/{TOKEN}"
    )

    await application.start()


if __name__ == "__main__":

    asyncio.run(setup_webhook())

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
    )
