from bot.handler import MessageHandler, CommandHandler, BotButtonCommandHandler
from bot.filter import Filter
import json

def register_handlers(dispatcher):

    def buttons_answer_cb(bot, event):
        if event.data['callbackData'] == "call_back_id_2":
            bot.answer_callback_query(
                query_id=event.data['queryId'],
                text="Hey! It's a working button 2.",
                show_alert=True
            )
        elif event.data['callbackData'] == "call_back_id_3":
            bot.answer_callback_query(
                query_id=event.data['queryId'],
                text="Hey! It's a working button 3.",
                show_alert=False
            )


    def command_cb(bot, event):
        bot.send_text(chat_id=event.from_chat, 
                      text="Привет! Я бот для создания автоматической рассылки пользователям.",
                      inline_keyboard_markup="{}".format(json.dumps([[
                      {"text": "Action 1", "url": "https://teams.vk.com"},
                      {"text": "Action 2", "callbackData": "call_back_id_2", "style": "attention"},
                      {"text": "Action 3", "callbackData": "call_back_id_2", "style": "primary"}
                  ]])))

    def message_cb(bot, event):
        bot.send_text(chat_id=event.from_chat, reply_msg_id=event.msgId, text="Это ответ на ваше сообщение с текстом: " + event.text)
    
    dispatcher.add_handler(CommandHandler(command="start", callback=command_cb))
    dispatcher.add_handler(MessageHandler(filters=Filter.text , callback=message_cb))
    dispatcher.add_handler(BotButtonCommandHandler(callback=buttons_answer_cb))
