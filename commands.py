from datetime import datetime, timedelta
import json
from bot.handler import MessageHandler, CommandHandler, BotButtonCommandHandler, StartCommandHandler
from bot.filter import Filter
from reporting import ReportManager
from scheduler import add_job, remove_all_jobs  # импортируем функцию для добавления задач

pending_schedule = {}  # хранение состояния ввода параметров рассылки

reporter = ReportManager()

def send_message(bot, chat_id, text):
    reporter.log_event("message_sent", {"chat_id": chat_id, "text": text})
    bot.send_text(chat_id=chat_id, text=text)

def register_handlers(dispatcher):

    def buttons_answer_cb(bot, event):
        reporter.log_event("button_click", {"chat_id": event.from_chat, "callback_data": event.data['callbackData']})
        if event.data['callbackData'] == "call_back_scheduler_delete":
            remove_all_jobs()
            bot.answer_callback_query(
                query_id=event.data['queryId'],
                text="Все запланированные рассылки удалены",
                show_alert=False
            )
            reporter.log_event("all_jobs_deleted", {"chat_id": event.from_chat})
        elif event.data['callbackData'] == "call_back_id_3":
            bot.answer_callback_query(
                query_id=event.data['queryId'],
                text="Hey! It's a working button 3.",
                show_alert=False
            )
        elif event.data['callbackData'] == "call_back_scheduler":
            send_message(bot, chat_id=event.from_chat, text="Введите корпоративные почты сотрудников, разделенные запятыми")
            pending_schedule[event.from_chat] = {"step": "emails"}

    def start_command_cb(bot, event):
        reporter.log_event("start_command", {"chat_id": event.from_chat, "inline_keyboard": True})
        bot.send_text(chat_id=event.from_chat, 
                      text="Привет! Я бот для создания автоматической рассылки пользователям.",
                      inline_keyboard_markup="{}".format(json.dumps([
                          [
                              {"text": "Запланировать рассылку", "callbackData": "call_back_scheduler", "style": "primary"},
                              {"text": "Удалить все \nзапланированные рассылки", "callbackData": "call_back_scheduler_delete", "style": "attention"},
                              {"text": "Action 3", "callbackData": "call_back_id_3", "style": "primary"}
                          ]
                      ]))
                    )

    def message_cb(bot, event):
        if pending_schedule.get(event.from_chat):
            state = pending_schedule[event.from_chat]
            if state.get("step") == "emails":
                # Парсим введённые корпоративные почты
                emails = [email.strip() for email in event.text.split(",") if email.strip()]
                state["emails"] = emails
                state["step"] = "datetime_msg"
                send_message(bot, event.from_chat, text="Введите дату и время (YYYY-MM-DD HH:MM) и сообщение через запятую")
                return
            elif state.get("step") == "datetime_msg":
                try:
                    dt_str, msg = event.text.split(",", 1)
                    dt_str = dt_str.strip()
                    msg = msg.strip()
                    now = datetime.now()
                    # Если строка содержит пробел, то считаем, что передана дата и время без года
                    if " " in dt_str:
                        date_part, time_part = dt_str.split(maxsplit=1)
                        date_part = date_part.replace(".", "-")
                        date_obj = datetime.strptime(f"{datetime.now().year}-{date_part}", "%Y-%d-%m")
                        time_part = time_part.replace(".", ":")
                        time_obj = datetime.strptime(time_part, "%H:%M").time()
                        scheduled_time = datetime.combine(date_obj.date(), time_obj)
                    else:
                        # Если введено только время
                        time_token = dt_str.replace(".", ":")
                        time_obj = datetime.strptime(time_token, "%H:%M").time()
                        scheduled_time = datetime.combine(now.date(), time_obj)
                        if scheduled_time <= now:
                            raise ValueError("Время уже прошло")
                    for email in state["emails"]:
                        msg = f"Для: {email}\n{msg}"
                        add_job(bot, scheduled_time, event.from_chat, msg)
                    send_message(bot, event.from_chat, text="Рассылка запланирована на {}".format(scheduled_time.strftime("%Y-%m-%d %H:%M")))
                except Exception as ex:
                    send_message(bot, event.from_chat, text="Ошибка формата. Используйте:\
                    \n• HH:MM, Текст сообщения, \
                    \n• DD-MM HH:MM, Текст сообщения, \
                    \n• YYYY-MM-DD HH:MM, Текст сообщения, \
                    \nгде HH:MM - время в 24-часовом формате")
                except ValueError as ex:
                    send_message(bot, event.from_chat, text="Время уже прошло")
                del pending_schedule[event.from_chat]
        else:
            send_message(bot, event.from_chat, text="Отвечаю на сообщение: {}".format(event.text))

    dispatcher.add_handler(StartCommandHandler(callback=start_command_cb))
    dispatcher.add_handler(MessageHandler(filters=Filter.text, callback=message_cb))
    dispatcher.add_handler(BotButtonCommandHandler(callback=buttons_answer_cb))
