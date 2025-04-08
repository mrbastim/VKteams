from datetime import datetime, timedelta
import re

from bot.handler import MessageHandler, CommandHandler, BotButtonCommandHandler, StartCommandHandler
from bot.filter import Filter
from bot.dispatcher import Dispatcher
from reporting import ReportManager
from scheduler import add_job, remove_all_jobs, scheduled_jobs
import keyboards

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
        # Обработка строки вида '@[email]\xa0' или '@[email]'
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
    now = datetime.now()
    dt_str = dt_str.strip().replace(".", "-").replace(" ", " ")
    msg = msg.strip()
    if " " in dt_str:
        date_part, time_part = dt_str.split(maxsplit=1)
        # Если год не указан, используем текущий год
        if len(date_part.split("-")) == 2:
            date_part = f"{now.year}-{date_part}"
        date_obj = datetime.strptime(date_part, "%Y-%m-%d")
        time_obj = datetime.strptime(time_part.replace(".", ":"), "%H:%M").time()
        scheduled_time = datetime.combine(date_obj.date(), time_obj)
    else:
        time_obj = datetime.strptime(dt_str.replace(".", ":"), "%H:%M").time()
        scheduled_time = datetime.combine(now.date(), time_obj)
    if scheduled_time <= now:
        raise ValueError("Дата и время уже прошли")
    return scheduled_time, msg

# Вспомогательные функции обработки шагов в сообщениях
def handle_emails_step(bot, chat_id, state, event):
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

def handle_conversation_step(bot, chat_id, state, event):
    pattern = r"https?://myteam\.mail\.ru/profile/([\w_]+)"
    links = [link.strip() for link in event.text.split(",")]
    chat_names = []
    for link in links:
        match = re.match(pattern, link)
        if match:
            chat_names.append(match.group(1))
        else:
            send_message(bot, chat_id, f"Неверный формат ссылки: {link}. Повторите ввод.")
            return
    state["conversation"] = chat_names
    state["step"] = "msg"
    send_message(bot, chat_id, "Введите текст сообщения для рассылки:")

def handle_message_input(bot, chat_id, state, event):
    state["msg"] = event.text.strip()
    state["step"] = "date"
    send_message(bot, chat_id, "Выберите дату для рассылки:", inline_keyboard=keyboards.date_choice)

def handle_custom_date_step(bot, chat_id, state, event):
    try:
        date_obj = datetime.strptime(event.text.strip(), "%Y-%m-%d").date()
        if date_obj < datetime.now().date():
            raise ValueError("Дата уже прошла")
        state["date"] = date_obj.strftime("%Y-%m-%d")
        state["step"] = "time"
        send_message(bot, chat_id, "Введите время (HH:MM или HH.MM) для рассылки:")
    except ValueError as ex:
        send_message(bot, chat_id, f"Ошибка: {ex}. Введите дату в формате YYYY-MM-DD:")

def handle_time_step(bot, chat_id, state, event):
    try:
        time_str = event.text.strip().replace(".", ":")
        scheduled_datetime = datetime.strptime(state["date"] + " " + time_str, "%Y-%m-%d %H:%M")
        now = datetime.now()
        if scheduled_datetime <= now:
            send_message(bot, chat_id, "Дата и время уже прошли")
            return
        if "emails" in state:
            for email in state["emails"]:
                msg_final = f"Сообщение от {chat_id}\n\n{state['msg']}"
                add_job(bot, scheduled_datetime, email, msg_final)
        elif "conversation" in state:
            for chat_name in state["conversation"]:
                msg_final = f"Сообщение от {chat_id}\n\n{state['msg']}"
                add_job(bot, scheduled_datetime, chat_name, msg_final)
        send_message(bot, chat_id, "Рассылка запланирована на " + scheduled_datetime.strftime("%Y-%m-%d %H:%M"))
    except ValueError as ex:
        bot.send_text(chat_id, text="Ошибка: " + str(ex) + "\nОбратитесь к администратору.")
        reporter.log_event("error", {"chat_id": chat_id, "error": str(ex)})
        pending_schedule.pop(chat_id, None)

def message_cb(bot, event):
    chat_id = event.from_chat
    state = pending_schedule.get(chat_id)
    if state:
        current_step = state.get("step")
        if current_step == "emails":
            handle_emails_step(bot, chat_id, state, event)
        elif current_step == "conversation":
            handle_conversation_step(bot, chat_id, state, event)
        elif current_step == "msg":
            handle_message_input(bot, chat_id, state, event)
        elif current_step == "custom_date":
            handle_custom_date_step(bot, chat_id, state, event)
        elif current_step == "time":
            handle_time_step(bot, chat_id, state, event)
        return
    # Если сообщение не является командным, отвечаем эхо-сообщением
    if not event.text.startswith("/"):
        send_message(bot, chat_id, "Отвечаю на ваше сообщение: " + event.text)
    elif event.text.startswith("/") and event.text != "/start" and event.text != "/new_message":
        # Если это команда, но не /start и не /new_message, отправляем сообщение об ошибке
        send_message(bot, chat_id, "Команда не распознана.")
        reporter.log_event("message_received", {"chat_id": chat_id, "text": event.text})

def buttons_answer_cb(bot, event):
    chat_id = event.from_chat
    data = event.data['callbackData']
    reporter.log_event("button_click", {"chat_id": chat_id, "callback_data": data})
    if data in ("today", "tomorrow"):
        state = pending_schedule.get(chat_id, {})
        if state.get("step") == "date":
            chosen_date = datetime.now().date() if data == "today" else (datetime.now() + timedelta(days=1)).date()
            state["date"] = chosen_date.strftime("%Y-%m-%d")
            state["step"] = "time"
            send_message(bot, chat_id, "Введите время (HH:MM или HH.MM) для рассылки:")
    elif data == "choose_date":
        state = pending_schedule.get(chat_id, {})
        if state.get("step") == "date":
            state["step"] = "custom_date"
            send_message(bot, chat_id, "Введите дату в формате YYYY-MM-DD:")
    elif data == "now":
        state = pending_schedule.get(chat_id, {})
        scheduled_datetime = datetime.now()
        if "emails" in state:
            for email in state["emails"]:
                msg_final = f"Сообщение от {chat_id}\n\n{state['msg']}"
                add_job(bot, scheduled_datetime, email, msg_final)
        elif "conversation" in state:
            for chat_name in state["conversation"]:
                msg_final = f"Сообщение от {chat_id}\n\n{state['msg']}"
                add_job(bot, scheduled_datetime, chat_name, msg_final)
        send_message(bot, chat_id, "Сообщение отправлено")
        pending_schedule.pop(chat_id, None)
    elif data == "call_back_scheduler_delete":
        remove_all_jobs()
        bot.answer_callback_query(
            query_id=event.data['queryId'],
            text="Все запланированные рассылки удалены",
            show_alert=False
        )
        reporter.log_event("all_jobs_deleted", {"chat_id": chat_id})
    elif data == "call_back_getjobs":
        if scheduled_jobs:
            text = "Запланированные рассылки:\n"
            for job in scheduled_jobs:
                text += f"- {job['email']}: {job['msg']} в {job['scheduled_time']}\n"
            bot.edit_text(chat_id, event.msgId, text=text, inline_keyboard_markup=keyboards.back_to_main)
            reporter.log_event("jobs_sent", {"chat_id": chat_id})
        else:
            bot.send_text(chat_id, text="Нет запланированных рассылок", inline_keyboard_markup=keyboards.back_to_main)
            reporter.log_event("no_jobs_sent", {"chat_id": chat_id})
    elif data == "call_back_scheduler":
        send_message(bot, chat_id, "Выберите действие", inline_keyboard=keyboards.email_choice)
    elif data == "send_personally":
        send_message(bot, chat_id, "Введите корпоративные почты сотрудников, разделенные запятыми")
        pending_schedule[chat_id] = {"step": "emails"}
    elif data == "send_to_conversation":
        send_message(bot, chat_id, "Введите ссылки на беседы через запятую")
        pending_schedule[chat_id] = {"step": "conversation"}
    elif data == "back_to_main":
        bot.edit_text(chat_id, event.msgId, text="Выберите действие", inline_keyboard_markup=keyboards.start)
        reporter.log_event("back_to_main", {"chat_id": chat_id})
        pending_schedule.pop(chat_id, None)

def start_command_cb(bot, event):
    reporter.log_event("start_command", {"chat_id": event.from_chat, "inline_keyboard": True})
    bot.send_text(chat_id=event.from_chat,
                  text="Привет! Я бот для создания автоматической рассылки пользователям.\nДоступные команды: /start /new_message",
                  inline_keyboard_markup=keyboards.start)

def new_msg_command_cb(bot, event):
    reporter.log_event("new_message_command", {"chat_id": event.from_chat, "inline_keyboard": True})
    bot.send_text(event.from_chat, text="Выберите действие", inline_keyboard_markup=keyboards.email_choice)

def register_handlers(dispatcher: Dispatcher):
    dispatcher.add_handler(CommandHandler(command="new_message", callback=new_msg_command_cb))
    dispatcher.add_handler(StartCommandHandler(callback=start_command_cb))
    dispatcher.add_handler(MessageHandler(filters=Filter.message, callback=message_cb))
    dispatcher.add_handler(BotButtonCommandHandler(callback=buttons_answer_cb))