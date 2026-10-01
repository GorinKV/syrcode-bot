"""Планировщик: утренний дайджест, напоминания, вечерний отчёт."""
import random
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from core.task_manager import (
    get_tasks_list,
    get_tasks_for_today,
    get_tasks_for_tomorrow,
    get_overdue_tasks,
    get_tasks_without_deadline,
    get_completed_today,
)

CHAT_ID_FILE = "data/chat_id.txt"

PRAISES = [
    "Ты сегодня отлично поработал! 💪",
    "Продуктивный день — так держать! 🔥",
    "С каждым днём ты становишься лучше! ⭐",
    "Отличный темп! Не сбавляй обороты! 🚀",
    "Даже маленькие шаги ведут к большой цели! 🧀",
    "Ты молодец, что находишь время на важное! 👏",
    "Сыр любит терпение, а дела — движение! Вперёд! 🧀",
    "Классная работа сегодня! Продолжай! ✨",
    "Ты вкладываешь в своё дело — это видно! 💎",
    "Ещё один день, ещё шаг к мечте! 🌟",
]

BLOG_IDEAS = [
    "Рецепт: сыр с трюфелем в домашних условиях",
    "5 ошибок начинающего сыровара",
    "Как выбрать молоко для сыра: полное руководство",
    "Сыр и вино: идеальные пары",
    "Зачем нужна закваска и чем она отличается от сычужного фермента",
    "Как хранить сыр дома, чтобы он не портился",
    "Домашний камамбер: пошаговый рецепт",
    "Бри vs Камамбер: в чём разница",
    "Мой первый сыр: что пошло не так",
    "Сырная тарелка: как её собрать красиво",
    "Сколько молока нужно на 1 кг сыра",
    "Как понять, что сыр готов",
    "Плесень на сыре: когда это хорошо, а когда — плохо",
    "Сыроварение как бизнес: с чего начать",
    "Инструменты сыровара: минимальный набор",
]


def _read_chat_id():
    try:
        with open(CHAT_ID_FILE) as f:
            return int(f.read().strip())
    except Exception:
        return None


def _format_task(t, idx):
    name = t.get("name") or t.get("title") or "(без названия)"
    tags = t.get("tags") or []
    prefix = "🔥 " if "важно" in tags else ""
    return f"{idx}. {prefix}{name}"


async def job_morning_digest(bot):
    chat_id = _read_chat_id()
    if not chat_id:
        print(">>> [scheduler] chat_id не найден, пропускаем утренний дайджест")
        return

    today = get_tasks_for_today()
    no_deadline = get_tasks_without_deadline()
    overdue = get_overdue_tasks()

    lines = ["☀️ Доброе утро!", ""]

    if overdue:
        lines.append("⚠️ Просрочено:")
        for i, t in enumerate(overdue, 1):
            lines.append(_format_task(t, i))
        lines.append("")

    if today:
        lines.append("📅 На сегодня:")
        for i, t in enumerate(today, 1):
            lines.append(_format_task(t, i))
        lines.append("")

    if no_deadline:
        lines.append("📌 Без срока:")
        for i, t in enumerate(no_deadline[:10], 1):
            lines.append(_format_task(t, i))
        lines.append("")

    if not (overdue or today or no_deadline):
        lines.append("📭 Задач нет — можно отдохнуть или придумать новое!")
        lines.append("")

    lines.append("💡 Идея для блога:")
    lines.append(random.choice(BLOG_IDEAS))

    try:
        await bot.send_message(chat_id, "\n".join(lines))
        print(f">>> [scheduler] Утренний дайджест отправлен в {chat_id}")
    except Exception as e:
        print(f">>> [scheduler] Ошибка утреннего дайджеста: {e}")


async def job_reminder(bot):
    """Всегда присылает: либо просроченные/завтра, либо 'задач нет'."""
    chat_id = _read_chat_id()
    if not chat_id:
        return

    tomorrow = get_tasks_for_tomorrow()
    overdue = get_overdue_tasks()
    all_tasks = get_tasks_list()

    lines = ["⏰ Проверка в 17:00", ""]

    if overdue:
        lines.append("⚠️ Просрочено:")
        for i, t in enumerate(overdue, 1):
            lines.append(_format_task(t, i))
        lines.append("")

    if tomorrow:
        lines.append("📅 На завтра:")
        for i, t in enumerate(tomorrow, 1):
            lines.append(_format_task(t, i))
        lines.append("")

    if not overdue and not tomorrow:
        if all_tasks:
            lines.append(f"✨ Срочных дел нет. Активных задач: {len(all_tasks)}.")
            lines.append("")
            lines.append("📋 Активные задачи:")
            for i, t in enumerate(all_tasks[:10], 1):
                lines.append(_format_task(t, i))
        else:
            lines.append("📭 Задач нет — чистый лист!")

    try:
        await bot.send_message(chat_id, "\n".join(lines).rstrip())
        print(">>> [scheduler] Напоминание отправлено")
    except Exception as e:
        print(f">>> [scheduler] Ошибка напоминания: {e}")


async def job_evening_report(bot):
    chat_id = _read_chat_id()
    if not chat_id:
        return

    completed = get_completed_today()
    active = get_tasks_list()

    lines = ["🌙 Вечерний отчёт", ""]

    if completed:
        lines.append(f"✅ Сделано сегодня: {len(completed)}")
        for i, t in enumerate(completed, 1):
            name = t.get("name") or "(без названия)"
            lines.append(f"{i}. {name}")
        lines.append("")

    if active:
        def sort_key(t):
            tags = t.get("tags") or []
            important = 0 if "важно" in tags else 1
            dl = t.get("deadline") or "9999-12-31T23:59:59"
            return (important, dl)
        active_sorted = sorted(active, key=sort_key)
        lines.append(f"📋 Осталось: {len(active_sorted)}")
        for i, t in enumerate(active_sorted[:10], 1):
            lines.append(_format_task(t, i))
        lines.append("")

    if not completed and not active:
        lines.append("Пустой день — тоже результат. Завтра новый старт! 🌱")
        lines.append("")

    if completed:
        lines.append(random.choice(PRAISES))
    elif active:
        lines.append("Задачи ждут — завтра наверстаем! 💪")
    else:
        lines.append("Отдых тоже важен! 🌙")

    try:
        await bot.send_message(chat_id, "\n".join(lines))
        print(">>> [scheduler] Вечерний отчёт отправлен")
    except Exception as e:
        print(f">>> [scheduler] Ошибка вечернего отчёта: {e}")


async def job_auto_commit(bot):
    try:
        from core import git_manager
        projects = git_manager._load_projects()
        if not projects:
            return
        result = await git_manager.auto_commit_all()
        if not result:
            return
        chat_id = _read_chat_id()
        if chat_id:
            await bot.send_message(chat_id, result)
            print(">>> [scheduler] Автокоммит выполнен")
    except Exception as e:
        print(f">>> [scheduler] Ошибка автокоммита: {e}")


def setup_scheduler(bot):
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    scheduler.add_job(
        job_morning_digest,
        CronTrigger(hour=7, minute=0),
        args=[bot],
        id="morning_digest",
        replace_existing=True,
    )
    scheduler.add_job(
        job_reminder,
        CronTrigger(hour=17, minute=0),
        args=[bot],
        id="reminder",
        replace_existing=True,
    )
    scheduler.add_job(
        job_evening_report,
        CronTrigger(hour=20, minute=40),
        args=[bot],
        id="evening_report",
        replace_existing=True,
    )
    scheduler.add_job(
        job_auto_commit,
        CronTrigger(hour="9-22", minute=0),
        args=[bot],
        id="auto_commit",
        replace_existing=True,
    )

    print(">>> [scheduler] Запланировано: 7:00, 17:00, 20:40 + автокоммит 9-22")
    return scheduler
