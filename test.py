from bot.bot import Bot
from bot.handler import MessageHandler, CommandHandler

TOKEN = "001.2064618793.3234805374:1011900609" #your token here

bot = Bot(token=TOKEN)

def command_cb(bot, event):
    bot.send_text(chat_id=event.from_chat, text="Привет! Я бот для создания автоматической рассылки пользователям.")

def message_cb(bot, event):
    bot.send_text(chat_id=event.from_chat, reply_msg_id = event.msgId, text="Это ответ на ваше сообщение с текстом: " + event.text)

bot.dispatcher.add_handler(CommandHandler(command="start", callback=command_cb))
bot.dispatcher.add_handler(MessageHandler(callback=message_cb))
bot.start_polling()

try:
    while True:
        pass
except KeyboardInterrupt:
    bot.stop()