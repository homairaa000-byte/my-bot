import os
import logging
import time
from datetime import datetime

import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

# =========================
# إعدادات
# =========================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TOKEN or not WEBHOOK_URL:
    raise Exception("Missing BOT_TOKEN or WEBHOOK_URL")

WEBHOOK_URL = WEBHOOK_URL.rstrip("/")
PORT = int(os.environ.get("PORT", 10000))

# =========================
# منع تكرار webhook (مهم جداً)
# =========================

WEBHOOK_SET = False
WEBHOOK_LAST_CHECK = 0

# =========================
# Telegram App
# =========================

application = (
    Application.builder()
    .token(TOKEN)
    .concurrent_updates(True)
    .build()
)

# =========================
# بيانات (RAM)
# =========================

chat_data = {}

def get_data(chat_id):
    if chat_id not in chat_data:
        chat_data[chat_id] = {
            "registered": {},
            "readers": set(),
            "listeners": {},
            "excused": {},
            "blocked": set(),
            "registration_open": True,
        }
    return chat_data[chat_id]

# =========================
# UI
# =========================

def menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✍️ سجل اسمي", callback_data="register"),
            InlineKeyboardButton("✅ قرأت", callback_data="read"),
        ],
        [
            InlineKeyboardButton("🎧 مستمعة", callback_data="listener"),
            InlineKeyboardButton("⛔️ معتذرة", callback_data="excused"),
        ],
        [
            InlineKeyboardButton("🧹 تصفير", callback_data="reset"),
            InlineKeyboardButton("🔒 قفل/فتح", callback_data="toggle"),
        ],
        [InlineKeyboardButton("❌ حذف", callback_data="remove")]
    ])

# =========================
# تنسيق
# =========================

def fmt(d):
    return "لا يوجد" if not d else "\n".join(f"{i+1}- {n}" for i, n in enumerate(d.values()))

def fmt_set(s):
    return "لا يوجد" if not s else "\n".join(f"{i+1}- {uid}" for i, uid in enumerate(s))

def build_text(chat_id):
    data = get_data(chat_id)
    now = datetime.now(pytz.timezone("Africa/Tripoli")).strftime("%Y-%m-%d %H:%M")

    return (
        f"📅 {now}\n\n"
        "خادم القرآن الرقمي 💫\n\n"
        f"✍️ المسجلات:\n{fmt(data['registered'])}\n\n"
        f"⛔️ المعتذرات:\n{fmt(data['excused'])}\n\n"
        f"🎧 المستمعات:\n{fmt(data['listeners'])}\n\n"
        f"✅ قرأت:\n{fmt_set(data['readers'])}"
    )

# =========================
# Callback Handler
# =========================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return

    await query.answer()

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    name = update.effective_user.full_name

    data = get_data(chat_id)

    if user_id in data["blocked"]:
        await query.answer("أنت محظورة", show_alert=True)
        return

    def clear():
        data["registered"].pop(user_id, None)
        data["listeners"].pop(user_id, None)
        data["excused"].pop(user_id, None)
        data["readers"].discard(user_id)

    try:
        if query.data == "register":
            if not data["registration_open"]:
                await query.answer("التسجيل مغلق", show_alert=True)
                return
            clear()
            data["registered"][user_id] = name

        elif query.data == "read":
            if user_id not in data["registered"]:
                await query.answer("سجل اسمك أولاً", show_alert=True)
                return

            if user_id in data["readers"]:
                data["readers"].remove(user_id)
                await query.answer("تم إلغاء قرأت")
            else:
                data["readers"].add(user_id)
                await query.answer("تم تسجيل قرأت")

        elif query.data == "listener":
            clear()
            data["listeners"][user_id] = name

        elif query.data == "excused":
            clear()
            data["excused"][user_id] = name

        elif query.data == "remove":
            clear()

        elif query.data == "reset":
            data["registered"].clear()
            data["listeners"].clear()
            data["excused"].clear()
            data["readers"].clear()

        elif query.data == "toggle":
            data["registration_open"] = not data["registration_open"]

        await query.edit_message_text(
            build_text(chat_id),
            reply_markup=menu()
        )

    except Exception as e:
        logger.error(f"Callback error: {e}")

# =========================
# WEBHOOK (PRODUCTION SAFE)
# =========================

async def post_init(app: Application):
    global WEBHOOK_SET, WEBHOOK_LAST_CHECK

    now = time.time()

    # منع إعادة التعيين المتكرر
    if WEBHOOK_SET and (now - WEBHOOK_LAST_CHECK < 120):
        logger.info("Webhook already set, skipping")
        return

    try:
        logger.info("Checking webhook...")

        info = await app.bot.get_webhook_info()
        target = f"{WEBHOOK_URL}/webhook/{TOKEN}"

        if info.url != target:
            logger.info("Setting webhook...")

            await app.bot.set_webhook(
                url=target,
                drop_pending_updates=True
            )

        WEBHOOK_SET = True
        WEBHOOK_LAST_CHECK = time.time()

        logger.info("Webhook ready")

    except Exception as e:
        logger.error(f"Webhook setup failed: {e}")

# =========================
# تشغيل
# =========================

def main():
    application.add_handler(CallbackQueryHandler(buttons))

    application.post_init = post_init

    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=f"webhook/{TOKEN}",
        webhook_url=f"{WEBHOOK_URL}/webhook/{TOKEN}",
        drop_pending_updates=True,
    )

if __name__ == "__main__":
    main()
