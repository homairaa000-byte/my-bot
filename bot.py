import os
import subprocess
from flask import Flask
from threading import Thread

# التوكن الخاص بك
BOT_TOKEN = '8817548868:AAHA4NrB7j28k7xSoIe2EVd3nZjZoA_rHJY'
PORT = int(os.environ.get("PORT", 8080))

app = Flask(__name__)

# هذا الخادم موجود فقط ليجعل Render سعيداً ويمنع إيقاف الخدمة
@app.route('/')
def home():
    return "البوت يعمل الآن بنجاح!"

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

if __name__ == '__main__':
    # 1. تشغيل خادم الويب (Flask) في الخلفية
    Thread(target=run_flask).start()
    
    # 2. تشغيل البوت في عملية منفصلة تماماً (Subprocess)
    # هذا ينهي مشكلة الـ Runtime Error للأبد
    subprocess.Popen(["python", "main_bot.py"])
