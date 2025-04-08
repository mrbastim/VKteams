from bot.bot import Bot
from config import TOKEN
from commands import register_handlers
import threading
import scheduler  

bot = Bot(token=TOKEN)

register_handlers(bot.dispatcher)
bot.start_polling()

scheduler_thread = threading.Thread(target=scheduler.start_scheduler, daemon=True)
scheduler_thread.start()

try:
    while True:
        pass
except Exception as e:
    bot.stop()
    print(e)
    exit()