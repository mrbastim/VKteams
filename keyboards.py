import json

start = "{}".format(json.dumps([
                          [
                              {"text": "Запланировать рассылку", "callbackData": "call_back_scheduler", "style": "primary"},
                              {"text": "Удалить все \nзапланированные рассылки", "callbackData": "call_back_scheduler_delete", "style": "attention"},
                              {"text": "Посмотреть \nзапланированные рассылки", "callbackData": "call_back_getjobs", "style": "primary"}
                          ]
                      ]))
date_choice = "{}".format(json.dumps([
    [
        {"text": "🗓️ Сегодня", "callbackData": "today", "style": "primary"},
        {"text": "🗓️ Завтра", "callbackData": "tomorrow", "style": "primary"}
    ],
    [
        {"text": "🗓️ Сейчас", "callbackData": "now", "style": "primary"},
    ],
    [
        {"text": "🔨 Выбрать дату вручную", "callbackData": "choose_date", "style": "primary"}
    ]
]))

email_choice = "{}".format(json.dumps([
    [
        {"text": "👤 Отправить в личные сообщения", "callbackData": "send_personally", "style": "primary"},
        {"text": "👥 Отправить в беседу", "callbackData": "send_to_conversation", "style": "primary"}
    ]
]))

back_to_main = "{}".format(json.dumps([
    [
        {"text": "Назад", "callbackData": "back_to_main", "style": "primary"}
    ]
]))