import logging
from telegram.ext import Application

TOKEN = "ضعي_التوكن_هنا"

async def main():
    application = Application.builder().token(TOKEN).build()
    bot_info = await application.bot.get_me()
    print(f"تم الاتصال بنجاح! اسم البوت: {bot_info.username}")

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
