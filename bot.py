import telebot

# نقوم بتعريف التوكن كجزئين ثم ندمجهما، بهذه الطريقة 
# لن يهم إذا قام الهاتف بكسر السطر أو لا
part1 = '8817548868'
part2 = ':AAEJYTdBHjvC6hdI6OD4s0neFOLWoOJtmYA'
TOKEN = part1 + part2

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "مرحباً! البوت يعمل الآن بكفاءة.")

@bot.message_handler(commands=['list'])
def send_list(message):
    bot.reply_to(message, "القائمة جاهزة.")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, f"وصلت رسالتك: {message.text}")

print("البوت يعمل الآن...")
bot.infinity_polling()
