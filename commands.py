from datetime import datetime, timedelta
import json
from bot.handler import MessageHandler, CommandHandler, BotButtonCommandHandler, StartCommandHandler
from bot.filter import Filter
from reporting import ReportManager
from scheduler import add_job, remove_all_jobs, scheduled_jobs
import keyboards
import re

pending_schedule = {}  # хранение состояний ввода для рассылки

reporter = ReportManager()

def send_message(bot, chat_id, text, inline_keyboard=None):
    reporter.log_event("message_sent", {"chat_id": chat_id, "text": text})
    bot.send_text(chat_id=chat_id, text=text, inline_keyboard_markup=inline_keyboard)

def parse_scheduled_input(input_text):
    """
    Парсит ввод вида "datetime, сообщение" и возвращает кортеж (scheduled_time, msg).
    Если дата/время уже прошли, выбрасывается ValueError.
    Форматы:
      - YYYY-MM-DD HH:MM, сообщение
      - HH:MM, сообщение  (тогда используется сегодняшняя дата)
    """
    try:
        dt_str, msg = input_text.split(",", 1)
    except Exception:
        raise ValueError("Неверный формат ввода. Ожидается разделение запятой.")
    dt_str = dt_str.strip()
    msg = msg.strip()
    now = datetime.now()
    # Если введена и дата и время (разделитель — пробел)
    if " " in dt_str:
        date_part, time_part = dt_str.split(maxsplit=1)
        date_part = date_part.replace(".", "-")
        # Используем текущий год, если год не указан
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
        raise ValueError("Дата и время уже прошли")
    return scheduled_time, msg

def register_handlers(dispatcher):

    def buttons_answer_cb(bot, event):
        reporter.log_event("button_click", {"chat_id": event.from_chat, "callback_data": event.data['callbackData']})
        # Обрабатываем выбор даты
        if event.data['callbackData'] in ("today", "tomorrow"):
            state = pending_schedule.get(event.from_chat, {})
            if state.get("step") == "date":
                if event.data['callbackData'] == "today":
                    chosen_date = datetime.now().date()
                else:
                    chosen_date = (datetime.now() + timedelta(days=1)).date()
                state["date"] = chosen_date.strftime("%Y-%m-%d")
                state["step"] = "time"
                send_message(bot, event.from_chat, text="Введите время (HH:MM или HH.MM) для рассылки:")
        elif event.data['callbackData'] == "choose_date":
            state = pending_schedule.get(event.from_chat, {})
            if state.get("step") == "date":
                state["step"] = "custom_date"
                send_message(bot, event.from_chat, text="Введите дату в формате YYYY-MM-DD:")
        elif event.data['callbackData'] == "call_back_scheduler_delete":
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
                text="{}".format(scheduled_jobs),
                show_alert=False
            )
        elif event.data['callbackData'] == "call_back_scheduler":
            send_message(bot, event.from_chat, text="Введите корпоративные почты сотрудников, разделенные запятыми")
            pending_schedule[event.from_chat] = {"step": "emails"}

    def start_command_cb(bot, event):
        reporter.log_event("start_command", {"chat_id": event.from_chat, "inline_keyboard": True})
        bot.send_text(chat_id=event.from_chat, 
                      text="Привет! Я бот для создания автоматической рассылки пользователям.",
                      inline_keyboard_markup=keyboards.start
                    )

    def message_cb(bot, event):
        chat_id = event.from_chat
        if pending_schedule.get(chat_id):
            state = pending_schedule[chat_id]
            # Шаг 1. Ввод почт
            if state.get("step") == "emails":
                email_regex = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$')
                emails = []
                for item in event.text.split(","):
                    email = item.strip()
                    # Обработка строки вида '@[email]\xa0' или '@[email]', когда пользователь вводится через @
                    if email.startswith('@[') and (email.endswith(']\xa0') or email.endswith(']')):
                        email = email[2:-2] if email.endswith(']\xa0') else email[2:-1]
                        email = email.strip()
                    if not email or not email_regex.match(email):
                        send_message(bot, chat_id, f"Неверный формат корпоративной почты: {email}. Повторите ввод.")
                        return
                    emails.append(email)
                if not emails:
                    send_message(bot, chat_id, "Не найдены корпоративные почты. Повторите ввод.")
                    return
                state["emails"] = emails
                state["step"] = "msg"
                send_message(bot, chat_id, "Введите текст сообщения для рассылки:")
                return
            # Шаг 2. Ввод сообщения
            elif state.get("step") == "msg":
                state["msg"] = event.text.strip()
                state["step"] = "date"
                send_message(bot, chat_id, "Выберите дату для рассылки:", inline_keyboard=keyboards.date_choice)
                return
            # Шаг 3. Ввод кастомной даты (если выбрано 'Выбрать дату вручную')
            elif state.get("step") == "custom_date":
                try:
                    # Проверяем формат даты
                    date_obj = datetime.strptime(event.text.strip(), "%Y-%m-%d").date()
                    if date_obj < datetime.now().date():
                        raise ValueError("Дата уже прошла")
                    state["date"] = date_obj.strftime("%Y-%m-%d")
                    state["step"] = "time"
                    send_message(bot, chat_id, "Введите время (HH:MM или HH.MM) для рассылки:")
                except ValueError as ex:
                    send_message(bot, chat_id, f"Ошибка: {ex}. Введите дату в формате YYYY-MM-DD:")
                return
            # Шаг 4. Ввод времени
            elif state.get("step") == "time":
                try:
                    time_str = event.text.strip().replace(".", ":")
                    # time_obj = datetime.strptime(time_str, "%H:%M").time()
                    # Объединяем введённую дату и время
                    scheduled_datetime = datetime.strptime(state["date"] + " " + time_str, "%Y-%m-%d %H:%M")
                    if scheduled_datetime <= datetime.now():
                        # raise ValueError("Дата и время уже прошли")
                        send_message(bot, chat_id, text="Дата и время уже прошли")
                    
                    for email in state["emails"]:
                        msg_final = f"Сообщение от {chat_id}\n\n {state['msg']}"
                        add_job(bot, scheduled_datetime, email, msg_final)
                    
                    send_message(bot, chat_id, text="Рассылка запланирована на {}".format(scheduled_datetime.strftime("%Y-%m-%d %H:%M")))
                except ValueError as ex:
                    send_message(bot, chat_id, text="Ошибка: " + str(ex) + "\nОбратитесь к администратору.")
                finally:
                    del pending_schedule[chat_id]
        else:
            send_message(bot, chat_id, text="Отвечаю на сообщение: {}".format(event.text))

    dispatcher.add_handler(StartCommandHandler(callback=start_command_cb))
    dispatcher.add_handler(MessageHandler(filters=Filter.text, callback=message_cb))
    dispatcher.add_handler(BotButtonCommandHandler(callback=buttons_answer_cb))
