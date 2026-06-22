import os
import asyncio
from aiohttp import web

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)

# =========================
# إعدادات
# =========================
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 10000))

# =========================
# أوامر البوت
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ البوت يعمل بنظام Webhook على Render")

# =========================
# إنشاء التطبيق
# =========================
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))

# =========================
# استقبال تحديثات تيليجرام
# =========================
async def handle(request):
    data = await request.json()

    update = Update.de_json(data, app.bot)

    await app.process_update(update)

    return web.Response(text="OK")

# =========================
# تشغيل Webhook
# =========================
async def run_webhook():

    # تهيئة البوت
    await app.initialize()
    await app.start()

    # ضبط الرابط لدى تيليجرام
    await app.bot.set_webhook(
        url=f"{WEBHOOK_URL}/{TOKEN}"
    )

    aio_app = web.Application()

    aio_app.router.add_post(
        f"/{TOKEN}",
        handle
    )

    # صفحة رئيسية
    async def home(request):
        return web.Response(text="Bot is running")

    aio_app.router.add_get("/", home)

    runner = web.AppRunner(aio_app)

    await runner.setup()

    site = web.TCPSite(
        runner,
        host="0.0.0.0",
        port=PORT
    )

    await site.start()

    print("🚀 Bot started")
    print(f"Webhook: {WEBHOOK_URL}/{TOKEN}")

    while True:
        await asyncio.sleep(3600)

# =========================
# التشغيل
# =========================
if __name__ == "__main__":
    asyncio.run(run_webhook())
