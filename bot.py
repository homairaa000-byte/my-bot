import asyncio
from aiohttp import web

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import TOKEN, WEBHOOK_URL, PORT


# =========================
# أوامر البوت
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 البوت يعمل بنظام Webhook V5")


# =========================
# التطبيق
# =========================
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))


# =========================
# Webhook handler (صحيح)
# =========================
async def handle(request):
    data = await request.json()

    update = Update.de_json(data, app.bot)
    await app.process_update(update)

    return web.Response(text="OK")


# =========================
# تشغيل السيرفر
# =========================
async def run_webhook():
    await app.bot.set_webhook(url=WEBHOOK_URL)

    aio_app = web.Application()
    aio_app.router.add_post(f"/{TOKEN}", handle)

    runner = web.AppRunner(aio_app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    print("🚀 Webhook running...")

    while True:
        await asyncio.sleep(3600)


# =========================
# main
# =========================
if __name__ == "__main__":
    asyncio.run(run_webhook())
