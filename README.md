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

## 🚀 Установка на новом сервере

### 1. Первичная настройка сервера

```bash
sudo bash ~/setup_server.sh
cd ~
git clone git@github.com:GorinKV/syrcode-bot.git
cd syrcode-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
~/restore.sh
# Выбрать режим 3 (только .env и config.py)
cd ~/syrcode-bot && cp README.md README.md.bak.$(date +%Y%m%d_%H%M%S) && cat > README.md << 'EOF'
# 🧀 СырКод — персональный ассистент сыровара

Telegram-бот на Python для ведения задач, идей и блога. Работает автономно на VPS, без зависимости от санкционных сервисов. Полностью бесплатный.

## ✨ Возможности

### 📋 Задачи
- Создание с естественного языка: «надо позвонить маме завтра»
- Сроки: завтра, через неделю, в пятницу, 15 октября, 15.10
- Важность: «важно», «срочно» → 🔥 приоритет
- Формат: `[ID] Название`, ID стабильный
- Удаление: `удали 4`, `/del 4`, «удали первую»
- Отметка: `/done 4`, «сделал 4», «выполнил второе»
- Возврат: `/undo N` — вернуть из выполненных

### 📊 Списки
- `/tasks` — активные
- `/all` — активные + выполненные
- `/completed` — только выполненные
- `/month`, `/year` — за период
- «за день», «сегодня», «за месяц», «за год» — короткие фразы

### 🎤 Голосовой ввод
- Локальное распознавание через whisper.cpp
- Модель подобрана под доступную RAM
- Работает офлайн, без внешних API

### ⏰ Автоматика (МСК)
- **04:00** — бэкап всего в Telegram
- **07:00** — утренний дайджест (задачи + идея для блога)
- **09:00–22:00, каждый час** — автокоммит git-проектов
- **17:00** — напоминание о сроках (всегда приходит)
- **20:40** — вечерний отчёт с похвалой

### 📦 Git-автокоммиты
- `/git add ~/project` — добавить проект
- `/git commit` — коммит с LLM-сообщением
- `/git status`, `/git list`, `/git auto`
- Раз в час бот сам коммитит изменения в отслеживаемых проектах

## 🏗️ Стек

| Компонент | Технология |
|---|---|
| Telegram-бот | aiogram 3 |
| LLM | GigaChat (Сбер), автообновление токена |
| Задачи | Taskdog (self-hosted, SQLite) |
| Речь | whisper.cpp (локально) |
| Прокси Telegram | tg-ws-proxy (SOCKS5) |
| Расписание | APScheduler |
| Git | GitPython |

## 📂 Структура проекта

**Основные файлы:**
- `main.py` — точка входа, aiogram-хендлеры
- `config.py` — чтение .env
- `requirements.txt`
- `.env.example` — шаблон (секретов нет)

**Папка `core/`:**
- `orchestrator.py` — GigaChat с авто-ретраем 401
- `gigachat_auth.py` — автообновление токена
- `task_manager.py` — Taskdog CRUD + история
- `natural_commands.py` — парсер NL-команд
- `date_parser.py` — даты и важность
- `voice_handler.py` — распознавание речи
- `scheduler.py` — автоотчёты и автокоммит
- `git_manager.py` — git-автокоммиты
- `file_keeper.py` — логирование

**Тесты:**
- `tests/test_parser.py` — 35 тестов парсера

**Данные (не в git):**
- `data/` — логи, chat_id, completed_log

## 🚀 Установка на новом сервере

### 1. Первичная настройка

    sudo bash ~/setup_server.sh

Создаст пользователей kvg, proxyuser, ftpuser, настроит SSH, FTP, tg-ws-proxy и swap.

### 2. Клонирование и зависимости

    cd ~
    git clone git@github.com:GorinKV/syrcode-bot.git
    cd syrcode-bot
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

### 3. Восстановление секретов

    ~/restore.sh
    # Режим 3 — только .env и config.py

Или вручную: скопировать `.env.example` в `.env` и заполнить ключи.

### 4. Внешние сервисы

Taskdog (трекер задач, порт 8100):

    uv tool install taskdog-ui[server]
    systemctl --user start taskdog-server

whisper.cpp (распознавание речи, порт 8080):

    git clone https://github.com/ggml-org/whisper.cpp.git
    cd whisper.cpp && cmake -B build && cmake --build build

tg-ws-proxy (SOCKS5 для Telegram, порт 1443):

    git clone https://github.com/Flowseal/tg-ws-proxy.git
    systemctl --user start tg-ws-proxy

### 5. Запуск бота

    sudo systemctl start syrcode-bot
    sudo systemctl status syrcode-bot

## 🛠 Управление

### Сервисы

    sudo systemctl restart syrcode-bot
    sudo journalctl -u syrcode-bot -f

    systemctl --user restart taskdog-server
    systemctl --user restart whisper-server
    systemctl --user restart tg-ws-proxy

### Бэкап

    ~/full_backup.sh       # полный бэкап
    ~/send_backup.py       # бэкап + отправка в Telegram
    ~/restore.sh           # восстановление

Автобэкап: cron, ежедневно в 04:00.

### Тесты

    cd ~/syrcode-bot
    source venv/bin/activate
    python tests/test_parser.py

Ожидается: Пройдено 35/35.

## 🎯 Команды бота

**Основные:**
- `/start`, `/help` — справка
- `/chatid` — узнать свой chat_id

**Задачи:**
- `/task Название` — создать
- `/tasks` — активные
- `/all` — активные + выполненные
- `/completed` — только выполненные
- `/month`, `/year` — за период
- `/done N` — отметить по ID
- `/undo N` — вернуть из выполненных
- `/del N` — удалить по ID
- `/clear` — удалить всё

**Git:**
- `/git add <путь>` — добавить проект
- `/git list` — список
- `/git status` — статус
- `/git commit` — коммит с LLM
- `/git auto` — автокоммит сейчас
- `/git remove <путь>` — убрать

## 🗣 Естественный язык

**Задачи:**
- «надо позвонить маме»
- «важно сварить сыр завтра»
- «срочно купить молоко до пятницы»
- «написать пост про камамбер»

**Списки:**
- «покажи задачи», «все задачи»
- «выполненные»
- «за день», «за месяц», «за год»

**Отметка и удаление:**
- «выполнил 4», «сделал второе»
- «удали 4», «удали первую задачу», «удали все задачи»

**Идеи:**
- «идея — сыр с трюфелем»
- «запиши идею про блог»

## 🔐 Безопасность

- Секреты только в `.env` (права 600, в `.gitignore`)
- Бэкап содержит `.env` — хранить в защищённом месте
- Опционально: шифрование бэкапа через GPG

## 📝 Принципы разработки

- Цельные файлы через `cat > file << 'EOF'`
- Точечные правки через `str.replace()`, не regex
- Бэкап перед правкой: `cp file file.bak.$(date +%Y%m%d_%H%M%S)`
- Проверка синтаксиса: `python -c "import ast; ast.parse(...)"`
- Тесты: 35 проверок в `tests/test_parser.py`
- Коммиты: осмысленные сообщения на русском

## 📄 Лицензия

MIT
