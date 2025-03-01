from bot.bot import Bot
from config import TOKEN
from commands import register_handlers
import threading
import time
import scheduler  

bot = Bot(token=TOKEN)

register_handlers(bot.dispatcher)
bot.start_polling()

scheduler_thread = threading.Thread(target=scheduler.start_scheduler, daemon=True)
scheduler_thread.start()

try:
    while True:
        time.sleep(1)
except Exception as e:
    bot.stop()
    exit(0)