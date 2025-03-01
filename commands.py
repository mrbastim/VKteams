from datetime import datetime, timedelta
import json
from bot.handler import MessageHandler, CommandHandler, BotButtonCommandHandler, StartCommandHandler
from bot.filter import Filter
from reporting import ReportManager
from scheduler import add_job  # импортируем функцию для добавления задач

pending_schedule = {}  # хранение ожидания ввода параметров рассылки

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
        elif event.data['callbackData'] == "call_back_scheduler":
            bot.send_text(chat_id=event.from_chat, text="Введите дату и время (YYYY-MM-DD HH:MM) и сообщение через запятую")
            pending_schedule[event.from_chat] = True

    def start_command_cb(bot, event):
        reporter.log_event("start_command", {"chat_id": event.from_chat, "inline_keyboard": True})
        bot.send_text(chat_id=event.from_chat, 
                      text="Привет! Я бот для создания автоматической рассылки пользователям.",
                      inline_keyboard_markup="{}".format(json.dumps([
                          [
                              {"text": "Запланировать рассылку\n Временно самому себе", "callbackData": "call_back_scheduler", "style": "primary"},
                              {"text": "Action 2", "callbackData": "call_back_id_2", "style": "attention"},
                              {"text": "Action 3", "callbackData": "call_back_id_3", "style": "primary"}
                          ]
                      ]))
                    )

    def message_cb(bot, event):
        if pending_schedule.get(event.from_chat):
            try:
                dt_str, msg = event.text.split(",", 1)
                dt_str = dt_str.strip()
                msg = msg.strip()
                now = datetime.now()
                # Если строка содержит пробел, то считаем, что передана дата и время без года
                if " " in dt_str:
                    date_part, time_part = dt_str.split(maxsplit=1)
                    # приводим разделитель даты к дефису
                    date_part = date_part.replace(".", "-")
                    # Пробуем создать дату с текущим годом
                    date_obj = datetime.strptime(f"{datetime.now().year}-{date_part}", "%Y-%d-%m")
                    # заменяем разделитель времени, если требуется
                    time_part = time_part.replace(".", ":")
                    time_obj = datetime.strptime(time_part, "%H:%M").time()
                    scheduled_time = datetime.combine(date_obj.date(), time_obj)
                else:
                    # Если введено только время
                    time_token = dt_str.replace(".", ":")
                    time_obj = datetime.strptime(time_token, "%H:%M").time()
                    scheduled_time = datetime.combine(now.date(), time_obj)
                    # Если время уже прошло, запланировать на следующий день
                    if scheduled_time <= now:
                        scheduled_time += timedelta(days=1)
                add_job(bot, scheduled_time, event.from_chat, msg)
                bot.send_text(chat_id=event.from_chat, text="Рассылка запланирована на {}".format(scheduled_time.strftime("%Y-%m-%d %H:%M")))
            except Exception as ex:
                bot.send_text(chat_id=event.from_chat, text="Ошибка формата. Используйте:\n• HH:MM, Текст сообщения\n• DD-MM HH:MM, Текст сообщения")
            del pending_schedule[event.from_chat]
        else:
            send_message(bot, event.from_chat, text="Отвечаю на сообщение: {}".format(event.text))

    dispatcher.add_handler(StartCommandHandler(callback=start_command_cb))
    dispatcher.add_handler(MessageHandler(filters=Filter.text, callback=message_cb))
    dispatcher.add_handler(BotButtonCommandHandler(callback=buttons_answer_cb))
