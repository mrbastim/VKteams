from bot.bot import Bot
from config import TOKEN
from commands import register_handlers
import threading
import scheduler  

bot = Bot(token=TOKEN)

register_handlers(bot.dispatcher)
bot.start_polling()

bot.send_text(chat_id="AoLI9L5XdY0EcyKSGVg", text="Bot started")
scheduler_thread = threading.Thread(target=scheduler.start_scheduler, daemon=True)
scheduler_thread.start()

try:
    while True:
        pass
except Exception as e:
    bot.stop()
    print(e)
    exit()