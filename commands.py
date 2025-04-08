from datetime import datetime, timedelta
from bot.handler import MessageHandler, CommandHandler, BotButtonCommandHandler, StartCommandHandler
from bot.filter import Filter
from bot.dispatcher import Dispatcher
from reporting import ReportManager
from scheduler import add_job, remove_all_jobs, scheduled_jobs
import keyboards
import re

pending_schedule = {}  # хранение состояний ввода для рассылки

reporter = ReportManager()

def send_message(bot, chat_id, text, inline_keyboard=None):
    """
    Отправляет сообщение в чат с указанным текстом и клавиатурой.
    Если inline_keyboard не передан, используется клавиатура по умолчанию.
    """
    reporter.log_event("message_sent", {"chat_id": chat_id, "text": text})
    bot.send_text(chat_id=chat_id, text=text, inline_keyboard_markup=inline_keyboard)

def extract_emails(bot, input_text, chat_id, email_regex):
    """
    Извлекает и проверяет корпоративные почты из строки.
    Если почта не соответствует формату, отправляет сообщение об ошибке.
    """
    emails = []
    for item in input_text.split(","):
        email = item.strip()
        # Обработка строки вида '@[email]\xa0' или '@[email]', когда пользователь вводит через @
        if email.startswith('@[') and (email.endswith(']\xa0') or email.endswith(']')):
            email = email[2:-2] if email.endswith(']\xa0') else email[2:-1]
            email = email.strip() 
        if not email or not email_regex.match(email):
            send_message(bot, chat_id, f"Неверный формат корпоративной почты: {email}. Повторите ввод.")
            return None
        emails.append(email)
    return emails

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

def register_handlers(dispatcher: Dispatcher):

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
        elif event.data['callbackData'] == "now":
            state = pending_schedule.get(event.from_chat, {})
            if state.get("step") == "date":
                # Используем текущее время для моментальной отправки
                scheduled_datetime = datetime.now()
                if "emails" in state:
                    for email in state["emails"]:
                        msg_final = f"Сообщение от {event.from_chat}\n\n {state['msg']}"
                        add_job(bot, scheduled_datetime, email, msg_final)
                else:
                    for chat_name in state["conversation"]:
                        msg_final = f"Сообщение от {event.from_chat}\n\n {state['msg']}"
                        add_job(bot, scheduled_datetime, chat_name, msg_final)
                send_message(bot, event.from_chat, text="Сообщение отправлено")
                del pending_schedule[event.from_chat]
                return
        elif event.data['callbackData'] == "call_back_scheduler_delete":
            remove_all_jobs()
            bot.answer_callback_query(
                query_id=event.data['queryId'],
                text="Все запланированные рассылки удалены",
                show_alert=False
            )
            reporter.log_event("all_jobs_deleted", {"chat_id": event.from_chat})
        elif event.data['callbackData'] == "call_back_getjobs":
            if scheduled_jobs:
                text = "Запланированные рассылки:\n"
                for job in scheduled_jobs:
                    text += f"- {job['email']}: {job['msg']} в {job['scheduled_time']}\n"
                bot.edit_text(event.from_chat, event.msgId, text=text, inline_keyboard_markup=keyboards.back_to_main)
                reporter.log_event("jobs_sent", {"chat_id": event.from_chat})
            else: 
                bot.edit_text(event.from_chat, event.msgId, text="Нет запланированных рассылок", inline_keyboard_markup=keyboards.back_to_main)
                reporter.log_event("no_jobs_sent", {"chat_id": event.from_chat})
        elif event.data['callbackData'] == "call_back_scheduler":
            send_message(bot, event.from_chat, text="Выберите действие", inline_keyboard=keyboards.email_choice)
        elif event.data['callbackData'] == "send_personally":
            send_message(bot, event.from_chat, text="Введите корпоративные почты сотрудников, разделенные запятыми")
            pending_schedule[event.from_chat] = {"step": "emails"}
        elif event.data['callbackData'] == "send_to_conversation":
            send_message(bot, event.from_chat, text="Введите ссылки на беседы через запятую")
            pending_schedule[event.from_chat] = {"step": "conversation"}
        elif event.data['callbackData'] == "back_to_main":
            bot.edit_text(event.from_chat, event.msgId, text="Выберите действие", inline_keyboard_markup=keyboards.start)
            reporter.log_event("back_to_main", {"chat_id": event.from_chat})
            if pending_schedule.get(event.from_chat):
                del pending_schedule[event.from_chat]           

    def start_command_cb(bot, event):
        reporter.log_event("start_command", {"chat_id": event.from_chat, "inline_keyboard": True})
        bot.send_text(chat_id=event.from_chat, 
                      text="Привет! Я бот для создания автоматической рассылки пользователям.",
                      inline_keyboard_markup=keyboards.start
                    )

    def new_msg_command_cb(bot, event):
        reporter.log_event("new_message_command", {"chat_id": event.from_chat, "inline_keyboard": True})
        bot.send_text(event.from_chat, text="Выберите действие", inline_keyboard_markup=keyboards.email_choice)

    def message_cb(bot, event):
        chat_id = event.from_chat
        if pending_schedule.get(chat_id):
            state = pending_schedule[chat_id]
            # Шаг 1. Ввод почт или ссылок на беседы
            if state.get("step") == "emails":
                email_regex = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$')
                emails = extract_emails(bot, event.text, chat_id, email_regex)
                if emails is None:
                    return
                if not emails:
                    send_message(bot, chat_id, "Не найдены корпоративные почты. Повторите ввод.")
                    return
                state["emails"] = emails
                state["step"] = "msg"
                send_message(bot, chat_id, "Введите текст сообщения для рассылки:")
                return
            elif state.get("step") == "conversation":
                pattern = r"https?://myteam\.mail\.ru/profile/([\w_]+)"
                links = [link.strip() for link in event.text.split(",")]
                chat_names = []
                for link in links:
                    match = re.match(pattern, link)
                    if match:
                        chat_names.append(match.group(1))
                    else:
                        send_message(bot, event.from_chat, f"Неверный формат ссылки: {link}. Повторите ввод.")
                        return
                state["conversation"] = chat_names
                state["step"] = "msg"
                send_message(bot, event.from_chat, text="Введите текст сообщения для рассылки:")
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
                    # Объединяем введённую дату и время
                    scheduled_datetime = datetime.strptime(state["date"] + " " + time_str, "%Y-%m-%d %H:%M")
                    if scheduled_datetime <= datetime.now():
                        # raise ValueError("Дата и время уже прошли")
                        send_message(bot, chat_id, text="Дата и время уже прошли")
                    if "emails" in state:
                        for email in state["emails"]:
                            msg_final = f"Сообщение от {chat_id}\n\n {state['msg']}"
                            add_job(bot, scheduled_datetime, email, msg_final)
                    else:
                        for chat_name in state["conversation"]:
                            msg_final = f"Сообщение от {chat_id}\n\n {state['msg']}"
                            add_job(bot, scheduled_datetime, chat_name, msg_final)
                    
                    send_message(bot, chat_id, text="Рассылка запланирована на {}".format(scheduled_datetime.strftime("%Y-%m-%d %H:%M")))
                except ValueError as ex:
                    bot.send_text(bot, chat_id, text="Ошибка: " + str(ex) + "\nОбратитесь к администратору.")
                    reporter.log_event("error", {"chat_id": chat_id, "error": str(ex)})
                    del pending_schedule[chat_id]

        elif not event.text.startswith("/"):
            send_message(bot, chat_id, text="Отвечаю на ваше сообщение: {}".format(event.text))
        else:
            send_message(bot, chat_id, text="Команда не распознана.")
            reporter.log_event("message_received", {"chat_id": chat_id, "text": event.text})

    dispatcher.add_handler(CommandHandler(command="new_message", callback=new_msg_command_cb))
    dispatcher.add_handler(StartCommandHandler(callback=start_command_cb))
    dispatcher.add_handler(MessageHandler(filters=Filter.message, callback=message_cb))
    dispatcher.add_handler(BotButtonCommandHandler(callback=buttons_answer_cb))
