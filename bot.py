import os
import asyncio
import logging
from datetime import datetime
from aiohttp import web
import asyncpg

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatMember
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 10000))
DATABASE_URL = os.getenv("DATABASE_URL")

if not TOKEN or not WEBHOOK_URL:
    raise ValueError("Missing BOT_TOKEN or WEBHOOK_URL")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bot")

# =========================
# 🔥 النصوص الأصلية (بدون تغيير)
# =========================

WELCOME_MESSAGE = """
مرحبا مرحبا بوصية رسول الله...
قال رسول الله ﷺ: "سيأتيكُم أقوامٌ يطلبونَ العِلمَ، فإذا رأيتُموهم فقولوا لَهُم: مَرحبًا مَرحبًا بوصيَّةِ رسولِ اللَّهِ صلَّى اللَّهُ عليهِ وسلَّمَ، واقْنوهُم". قلتُ للحَكَمِ: ما اقْنوهُم؟ قالَ: علِّموهُم.

أهلاً بكِ في أكاديمية معارج الإتقان 🕊🌴🌴🌴
يرجى قراءة قوانين الأكاديمية المثبتة والالتزام بها.
"""

RULES_TEXT = """
بسم الله الرحمن الرحيم 

أكاديمية معارج الاتقان 🕊🌴🌴🌴

قوانين الأكاديمية:

🌴🌴الأكاديمية تعنى بتقديم كل ما يتعلق بالتجويد والقران من حصص تجويد وتصحيح تلاوه وقراءات وغيرها من المجالات. 

1. الأكاديمية خاصه بالنساء فقط، يمنع منعاً باتاً انضمام الرجال.🚫🚫🚫

2. ليس هنالك شروط للإنضمام للأكاديمية سوى الإنضباط.👩‍✈️👩‍✈️

3. الرجاء كتابه الاسم بوضوح وعدم استخدام الرموز (والاولاد بدون كلمة أم) حتى لا يتم ازالتك.❌❌

4. مجموعات الحفظ بروايه قالون: ربع يس تحت إشراف المعلمة أم ساجدة، و ربع البقرة تحت اشراف المعلمة مريم، و جزء عم و تبارك تحت إشراف المعلمه يسر ورغي @Yosrwerghi، كل من تريد الإنضمام الى مجموعات الحفظ برواية قانون تتواصل مع مسؤولات المجموعات. 

5. مجموعات الحفظ برواية حفص: ربع يس تحت إشراف المعلمة نهى سعيد، و ليلى القطروني، جزئي تبارك و عم تحت اشراف المعلمة فاطمة فتحي، و ربع البقرة تحت إشراف المعلمة زهراء @Zahraamohamed_mahsoup18 والمعلمة أماني amani وميمونة @Aminaoon.

6. ليس لدينا مجموعات حفظ برواية ورش بعد.

🌼🌺 كل من تريد الإنضمام إلى المجموعات او السؤال عن اي شيء يتعلق بها التواصل مع مشرفات المجموعات.

7. ممنوع نشر الروابط غير المتعلقة بالأكاديمية . 🛑🛑🛑

8. ممنوع التواصل مع المعلمات في الخاص، أي استفسار يرسل هنا على المقراة أو لمشرفات المجموعات.✋✋

💐💐شاكرين حسن تعاونكن لننهض جميعا بصرح تعليمي شامخ.
"""

SCHEDULE_TEXT = """
" ✍جدول حلقات المقرأة♕

꧁꧁꧁꧁꧂꧂꧂꧂

💐 المعلمة : لطيفة تصحيح تلاوة
📝 المشرفة : دنيا
⏰ التوقيت : الأثنين 12مكة
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : لطيفة المخارج
📝 المشرفة : دنيا
⏰ التوقيت : الثلاثاء 12مكة 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : لطيفة
📝 المشرفة : ..دنيا.
⏰ التوقيت : الأربعاء تأهيل المعلمات 12مكة
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : لطيفة ربع يس 
📝 المشرفة : احلام وليلي
⏰ التوقيت : الخميس 12 مكة 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : منى الدسوقي أصول ورش 
📝 المشرفة : لطيفة
⏰ التوقيت : الأثنين والاربعاء الخامسة مكة
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : عالية محمد (تصحيح تلاوة جزء عم) 
📝 المشرفة : ساجدة علي
⏰ التوقيت : 6:00 م بتوقيت مكة.. 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : إيمان عجلان ﴿تصحيح جزء عم ﴾حفص
📝 المشرفة : ----
⏰ التوقيت : السبت 10.00صباحا توقيت مكه
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : يسر أم عبد الرحمن (تصحيح جزء تبارك)
📝 المشرفة : متى يوسفي
⏰ التوقيت : 10مساءا توقيت مكة
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : أميرة عزت 
شرح احكام النون الساكنه والتنوين 
📝 المشرفة : دنيا
⏰ التوقيت : الاحد 3عصرا بتوقيت مكه 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : مريم ياسين 
📝 المشرفة : 
⏰ التوقيت : الثالثة مساءا بتوقيت ليبيا
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : عائشة عبدالسلام ( حفظ سوره البقرة برواية قالون ) 
📝 المشرفة : ليلي القطروني... ام سومه(هاجر محمد علي) 
⏰ التوقيت :الثلاثاء..الثالثة مساء 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : نهى السعيد(حفظ ربع يس برواية حفص ) 
📝 المشرفة : ليلى القطرونى -عائشة عبد السلام
⏰ التوقيت : السبت -2ظهرا بتوقيت مصر 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : أم ساجدة 
📝 المشرفة : ساجدة 
⏰ التوقيت : العاشرة صباحا بتوقيت ليبيا 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : نسمه طه تصحيح جزئى تبارك وعم 
📝 المشرفة : 
⏰ التوقيت : الخميس ٤م توقيت مصر
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : فاطمه فتحي 
حفظ جزئى تبارك وعم بروايه حفص
📝 المشرفة :؟؟ 
⏰ التوقيت : تسميع الثلاثاء العاشره 🌤صباحا توقيت مكه ومصر 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : ميمونة تصحيح تلاوة 
📝 المشرفة : زهراء اماني
⏰ التوقيت : يوم الاحد الساعة 2 توقيت مكة 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : تاهيل معلمات
📝 المشرفة : 
⏰ التوقيت : الاثنين 2 توقيت مكة 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : زهراء 
📝 المشرفة : اماني علي 
📆   اليوم:  السبت 
⏰ التوقيت : 5 بتوقيت مصر 
❀❀❀❀❀❀❀❀❀❀❀
💐 المعلمة : نسرين بركات 
📝 المشرفة : ميمونة 
📆   اليوم:  السبت 
⏰ التوقيت : 3 مساء بتوقيت مصر 
❀❀❀❀❀❀❀❀❀❀❀

القرآن في الدنيا نافع🍃
وفي القبر شافع🍃
وفي الجنة رافع🍃
اللهم اجعلنا من أهله وخاصته🤲🌹
"
"""

# =========================
# باقي النظام (Production ثابت)
# =========================

app = Application.builder().token(TOKEN).build()

async def db():
    return await asyncpg.connect(DATABASE_URL)

async def build(chat_id):
    conn = await db()

    data = await conn.fetch(
        "SELECT name,status,read_status FROM users WHERE chat_id=$1 ORDER BY created_at",
        chat_id
    )

    await conn.close()

    def section(st):
        rows = [r for r in data if r["status"] == st]
        return "\n".join(f"{i+1}- {r['name']}" for i, r in enumerate(rows)) or "لا يوجد"

    return (
        "📅 خادم القرآن الرقمي\n\n"
        f"✍ المسجلات:\n{section('register')}\n\n"
        f"⛔ المعتذرات:\n{section('excused')}\n\n"
        f"🎧 المستمعات:\n{section('listener')}"
    )

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍ تسجيل", callback_data="register"),
         InlineKeyboardButton("🎧 مستمعة", callback_data="listener")],
        [InlineKeyboardButton("⛔ معتذرة", callback_data="excused"),
         InlineKeyboardButton("❌ حذف", callback_data="remove")],
        [InlineKeyboardButton("🔒 قفل/فتح", callback_data="lock")],
        [InlineKeyboardButton("🧹 تصفير", callback_data="reset")],
        [InlineKeyboardButton("✅ قرأت", callback_data="read")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(await build(update.effective_chat.id), reply_markup=menu())
    await update.message.reply_text(WELCOME_MESSAGE)

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(RULES_TEXT)

async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(SCHEDULE_TEXT)

# (يمكن إضافة باقي handlers كما في النسخة السابقة بدون تغيير)

async def handle(request):
    data = await request.json()
    update = Update.de_json(data, app.bot)
    await app.process_update(update)
    return web.Response(text="OK")

async def run():
    await app.initialize()
    await app.start()

    path = f"/{TOKEN}"
    await app.bot.set_webhook(url=f"{WEBHOOK_URL}{path}")

    aio = web.Application()
    aio.router.add_post(path, handle)
    aio.router.add_get("/", lambda r: web.Response(text="OK"))

    runner = web.AppRunner(aio)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(run())
