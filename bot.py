import os
import logging
from flask import Flask
from threading import Thread
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# إعداد السجلات لمراقبة الأخطاء
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ==========================================
# 1. نظام ويب بسيط لـ Render
# ==========================================
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "البوت يعمل بكفاءة!"

def run_flask():
    # Render يخصص منفذاً تلقائياً، يجب استخدامه
    port = int(os.environ.get("PORT", 8080))
    app_flask.run(host='0.0.0.0', port=port)

# ==========================================
# 2. وظائف البوت (كما طلبتِ)
# ==========================================
async def is_user_admin(update, context, user_id):
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
        return member.status in ['administrator', 'creator']
    except:
        return False

async def filter_group_links(update, context):
    message = update.effective_message
    if not message: return
    user_id = update.effective_user.id
    
    # التحقق من الروابط
    has_link = any(e.type in ['url', 'text_link'] for e in (message.entities or []))
    
    if has_link and not await is_user_admin(update, context, user_id):
        try:
            await message.delete()
            await context.bot.send_message(update.effective_chat.id, "⚠️ تم حذف الرابط: ممنوع لغير المشرفات.")
        except: pass

# ==========================================
# 3. التشغيل الرئيسي
# ==========================================
def main():
    # تشغيل Flask في الخلفية
    Thread(target=run_flask).start()

    # التوكن الجديد
    BOT_TOKEN = "8817548868:AAEBP-C8ift1Z-_ydpDzmticw18gDW2_Kjc"

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT, filter_group_links))

    print("🚀 البوت الآن يعمل على السحابة!")
    app.run_polling()

if __name__ == '__main__':
    main()
