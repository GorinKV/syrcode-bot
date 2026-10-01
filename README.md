# СырКод — персональный ассистент сыровара

Telegram-бот на Python, который помогает вести задачи, идеи и блог сыровара.

## Возможности

- 📋 **Задачи** — создание, удаление, отметка выполненными
- ⏰ **Сроки и важность** — «завтра», «до пятницы», «важно»
- 💡 **Идеи** — запись мыслей с голоса или текста
- 🎤 **Голосовой ввод** — локальное распознавание через whisper.cpp
- 📊 **История** — выполненные за день/месяц/год
- 🕐 **Автоотчёты** — утренний дайджест, напоминания, вечерний отчёт
- 🤖 **Естественный язык** — «надо позвонить маме завтра»

## Стек

- **aiogram 3** — Telegram-бот
- **GigaChat** — LLM (Сбер)
- **Taskdog** — локальный трекер задач
- **whisper.cpp** — распознавание речи
- **APScheduler** — расписание
- **tg-ws-proxy** — прокси для Telegram (SOCKS5)

## Установка

```bash
git clone <твой_репозиторий> syrcode-bot
cd syrcode-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Заполни .env своими ключами

# Настрой Taskdog, tg-ws-proxy, whisper.cpp
# (см. отдельные инструкции)
syrcode-bot/
├── main.py                 # точка входа, хендлеры aiogram
├── config.py               # чтение переменных из .env
├── requirements.txt
├── .env.example            # шаблон (секретов нет)
├── core/
│   ├── orchestrator.py     # GigaChat
│   ├── task_manager.py     # работа с Taskdog
│   ├── natural_commands.py # парсер NL-команд
│   ├── date_parser.py      # парсер дат и важности
│   ├── voice_handler.py    # распознавание речи
│   ├── scheduler.py        # автоотчёты
│   ├── file_keeper.py      # логирование
│   └── gigachat_auth.py    # автообновление токена
└── data/                   # логи и чаты (не в git)

Команды

· /start, /help — справка
· /tasks — активные задачи
· /all — активные + выполненные
· /completed — только выполненные
· /month, /year — за месяц/год
· /task <название> — создать
· /done <ID> — отметить выполненной
· /del <ID> — удалить
· /clear — удалить всё

Лицензия

MIT
