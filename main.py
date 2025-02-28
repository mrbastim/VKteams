from bot.bot import Bot
from config import TOKEN
from commands import register_handlers

bot = Bot(token=TOKEN)


register_handlers(bot.dispatcher)
bot.start_polling()

try:
    while True:
        pass
except Exception as e:
    bot.stop()
    exit(0)