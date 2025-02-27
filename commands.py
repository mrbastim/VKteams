from bot.handler import MessageHandler, CommandHandler

def register_handlers(dispatcher):
    def command_cb(bot, event):
        bot.send_text(chat_id=event.from_chat, text="Привет! Я бот для создания автоматической рассылки пользователям.")

    def message_cb(bot, event):
        bot.send_text(chat_id=event.from_chat, reply_msg_id=event.msgId, text="Это ответ на ваше сообщение с текстом: " + event.text)

    dispatcher.add_handler(CommandHandler(command="start", callback=command_cb))
    dispatcher.add_handler(MessageHandler(callback=message_cb))