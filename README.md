# VKTeams Project

## Overview

Проект для автоматической рассылки сообщений пользователям ВКонтакте с возможностью планирования рассылок по заданной дате и времени.
Поддерживается два способа логирования:

- Локальное логирование в файлы JSON (reporting.py)
- Логирование через PostgreSQL (reporting_psycorg2.py, опционально)

## File Structure

```text
VKTeams/
├── bot/
│      ├── bot.py
│      ├── handler.py
│      └── filter.py
├── config.py
├── commands.py
├── main.py
├── reporting.py          # Логи пишутся в JSON файлы в каталоге logs/
├── reporting_psycorg2.py # Реализация логирования через PostgreSQL (опционально)
├── scheduler.py
├── keyboards.py
├── requirements.txt
├── .gitignore
└── logs/                # Логи формируются автоматически
```

## Setup and Usage

1. Убедитесь, что все необходимые зависимости установлены (см. файл [requirements.txt](d:/Сеть/_Учеба/Python/VKteams/requirements.txt)).
2. Для использования логирования через PostgreSQL, раскомментируйте соответствующие параметры в файле config.py и установите PostgreSQL.
3. Запустите проект, выполнив:

```sh
python main.py
```

**Внимание!**
При остановке бота все запланированные рассылки *автоматически удаляются* из памяти.
