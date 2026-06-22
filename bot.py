import os
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from handlers.start import start

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")


# ===== Web server بسيط لـ Render =====
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")


def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()


# ===== Telegram bot =====
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    # تشغيل السيرفر + البوت معًا
    threading.Thread(target=run_server).start()

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
