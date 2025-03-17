import json

start = "{}".format(json.dumps([
                          [
                              {"text": "Запланировать рассылку", "callbackData": "call_back_scheduler", "style": "primary"},
                              {"text": "Удалить все \nзапланированные рассылки", "callbackData": "call_back_scheduler_delete", "style": "attention"},
                              {"text": "Action 3", "callbackData": "call_back_id_3", "style": "primary"}
                          ]
                      ]))
date_choice = "{}".format(json.dumps([
    [
        {"text": "🗓️ Сегодня", "callbackData": "today", "style": "primary"},
        {"text": "🗓️ Завтра", "callbackData": "tomorrow", "style": "primary"}
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