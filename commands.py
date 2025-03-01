from bot.handler import MessageHandler, CommandHandler, BotButtonCommandHandler, StartCommandHandler
from bot.filter import Filter
from reporting import ReportManager
import json

reporter = ReportManager()
def send_message(bot, chat_id, text):
    reporter.log_event("message_sent", {"chat_id": chat_id, "text": text})
    bot.send_text(chat_id=chat_id, text=text)

def register_handlers(dispatcher):

    def buttons_answer_cb(bot, event):
        reporter.log_event("button_click", {"chat_id": event.from_chat, "callback_data": event.data['callbackData']})
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

    def start_command_cb(bot, event):
        reporter.log_event("start_command", {"chat_id": event.from_chat, "inline_keyboard": True})
        bot.send_text(chat_id=event.from_chat, 
                      text="Привет! Я бот для создания автоматической рассылки пользователям.",
                      inline_keyboard_markup="{}".format(json.dumps([
                        [
                            {"text": "Action 1", "url": "https://teams.vk.com"},
                            {"text": "Action 2", "callbackData": "call_back_id_2", "style": "attention"},
                            {"text": "Action 3", "callbackData": "call_back_id_3", "style": "primary"}
                        ]
                        ]))
                    )

    def message_cb(bot, event):
        send_message(bot, event.from_chat, text="Отвечаю на сообщение: {}".format(event.text))
        
    dispatcher.add_handler(StartCommandHandler(callback=start_command_cb))
    dispatcher.add_handler(MessageHandler(filters=Filter.text , callback=message_cb))
    dispatcher.add_handler(BotButtonCommandHandler(callback=buttons_answer_cb))
