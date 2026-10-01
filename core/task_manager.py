import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
import httpx
from config import TASKDOG_API_URL, TASKDOG_API_KEY

HEADERS = {
    "X-Api-Key": TASKDOG_API_KEY,
    "Content-Type": "application/json",
}

COMPLETED_LOG = "data/completed_log.json"

RU_MONTHS = {
    1: "январь", 2: "февраль", 3: "март", 4: "апрель",
    5: "май", 6: "июнь", 7: "июль", 8: "август",
    9: "сентябрь", 10: "октябрь", 11: "ноябрь", 12: "декабрь",
}

RU_MONTHS_GEN = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}


def _extract_tasks(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("tasks", "items", "results", "data"):
            if key in data and isinstance(data[key], list):
                return data[key]
        if "id" in data and "name" in data:
            return [data]
    return []


def _format_deadline(iso_str):
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return iso_str[:10]


def _sort_tasks(tasks):
    """Важные сверху, потом по сроку, потом без срока."""
    def sort_key(t):
        tags = t.get("tags") or []
        important = 0 if "важно" in tags else 1
        dl = t.get("deadline") or "9999-12-31T23:59:59"
        return (important, dl)
    return sorted(tasks, key=sort_key)


def _log_completed(name, task_id):
    os.makedirs(os.path.dirname(COMPLETED_LOG), exist_ok=True)
    try:
        with open(COMPLETED_LOG) as f:
            data = json.load(f)
    except Exception:
        data = []
    data.append({
        "id": task_id,
        "name": name,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M"),
    })
    cutoff = (datetime.now() - timedelta(days=365 * 2)).strftime("%Y-%m-%d")
    data = [d for d in data if d.get("date", "") >= cutoff]
    with open(COMPLETED_LOG, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _read_completed_log():
    try:
        with open(COMPLETED_LOG) as f:
            return json.load(f)
    except Exception:
        return []


def get_tasks_list():
    """Активные задачи, отсортированные."""
    try:
        response = httpx.get(
            f"{TASKDOG_API_URL}/api/v1/tasks",
            headers=HEADERS,
            timeout=10,
            follow_redirects=True,
        )
        response.raise_for_status()
        return _sort_tasks(_extract_tasks(response.json()))
    except Exception:
        return []


def _delete_by_id(task_id):
    """Удаляет задачу по внутреннему ID. Возвращает 'ok' или ошибку."""
    try:
        response = httpx.delete(
            f"{TASKDOG_API_URL}/api/v1/tasks/{task_id}",
            headers=HEADERS,
            timeout=10,
            follow_redirects=True,
        )
        if response.status_code in (200, 204):
            return "ok"
        if response.status_code == 404:
            return "⚠️ Задача не найдена."
        response.raise_for_status()
        return "ok"
    except Exception as e:
        return f"⚠️ Ошибка Taskdog: {e}"


def _patch_done(task_id):
    """Помечает задачу COMPLETED по внутреннему ID."""
    try:
        response = httpx.patch(
            f"{TASKDOG_API_URL}/api/v1/tasks/{task_id}",
            json={"status": "COMPLETED"},
            headers=HEADERS,
            timeout=10,
            follow_redirects=True,
        )
        if response.status_code >= 400:
            r2 = httpx.delete(
                f"{TASKDOG_API_URL}/api/v1/tasks/{task_id}",
                headers=HEADERS,
                timeout=10,
                follow_redirects=True,
            )
            if r2.status_code not in (200, 204):
                return f"⚠️ Не удалось отметить: {response.text[:200]}"
        return "ok"
    except Exception as e:
        return f"⚠️ Ошибка Taskdog: {e}"


def add_task(title, notes="", deadline=None, important=False):
    """Создаёт задачу, возвращает подтверждение с ID."""
    try:
        payload = {"name": title}
        payload["priority"] = 1 if important else 5
        if deadline:
            payload["deadline"] = deadline
        if important:
            payload["tags"] = ["важно"]
        if notes:
            payload["notes"] = notes

        response = httpx.post(
            f"{TASKDOG_API_URL}/api/v1/tasks",
            json=payload,
            headers=HEADERS,
            timeout=10,
            follow_redirects=True,
        )
        response.raise_for_status()
        task = response.json()
        task_name = task.get("name") or task.get("title") or title
        task_id = task.get("id", "?")

        suffix = []
        if important:
            suffix.append("🔥 важно")
        if deadline:
            suffix.append(f"срок: {_format_deadline(deadline)}")
        suffix_str = f" ({', '.join(suffix)})" if suffix else ""

        return f"✅ Задача создана: [{task_id}] — {task_name}{suffix_str}"
    except Exception as e:
        return f"⚠️ Ошибка Taskdog: {e}"


def list_tasks(sort_by_deadline=True):
    """Список активных задач."""
    try:
        tasks = get_tasks_list()
        if not tasks:
            return "📭 Активных задач нет."

        lines = ["📋 Активные задачи:"]
        for t in tasks[:20]:
            name = t.get("name") or t.get("title") or "(без названия)"
            real_id = t.get("id", "?")
            tags = t.get("tags") or []
            prefix = "🔥 " if "важно" in tags else ""
            suffix_parts = []
            if t.get("deadline"):
                suffix_parts.append(f"до {_format_deadline(t['deadline'])}")
            suffix = f" ({', '.join(suffix_parts)})" if suffix_parts else ""
            lines.append(f"[{real_id}] {prefix}{name}{suffix}")
        return "\n".join(lines)
    except Exception as e:
        return f"⚠️ Ошибка Taskdog: {e}"


def resolve_and_delete(command):
    """Удаление по ID, позиции или имени."""
    action = command.get("action")

    if action == "clear_all":
        return clear_tasks()

    tasks = get_tasks_list()
    if not tasks:
        return "📭 Задач нет — нечего удалять."

    # По ID (delete_by_real_id) или по позиции (delete_by_ordinal)
    if action in ("delete_by_real_id", "delete_by_id", "delete_by_ordinal"):
        if action == "delete_by_ordinal":
            idx = command["ordinal"]
            if idx == -1:
                idx = len(tasks)
            if idx < 1 or idx > len(tasks):
                return f"⚠️ Задачи №{idx} нет. Всего задач: {len(tasks)}."
            target_id = tasks[idx - 1]["id"]
        else:
            target_id = command["id"]
            if not any(t.get("id") == target_id for t in tasks):
                return f"⚠️ Задача [{target_id}] не найдена."
        result = _delete_by_id(target_id)
        if result == "ok":
            return f"🗑️ Задача [{target_id}] удалена."
        return result

    if action == "delete_by_name":
        name_query = command["name"].lower()
        matches = [t for t in tasks if name_query in (t.get("name") or "").lower()]
        if not matches:
            return f"⚠️ Задача «{command['name']}» не найдена."
        if len(matches) > 1:
            lines = ["Найдено несколько, уточни ID:"]
            for m in matches:
                lines.append(f"  [{m['id']}] {m['name']}")
            return "\n".join(lines)
        target = matches[0]
        result = _delete_by_id(target["id"])
        if result == "ok":
            return f"🗑️ Задача [{target['id']}] удалена."
        return result

    return "⚠️ Не понял команду удаления."


def clear_tasks():
    """Удаляет ВСЕ задачи."""
    try:
        tasks = get_tasks_list()
        if not tasks:
            return "📭 Задач нет — нечего удалять."
        deleted = 0
        failed = 0
        for t in tasks:
            tid = t.get("id")
            if tid is None:
                continue
            r = httpx.delete(
                f"{TASKDOG_API_URL}/api/v1/tasks/{tid}",
                headers=HEADERS,
                timeout=10,
                follow_redirects=True,
            )
            if r.status_code in (200, 204):
                deleted += 1
            else:
                failed += 1
        msg = f"🗑️ Удалено задач: {deleted}"
        if failed:
            msg += f"\n⚠️ Не удалось удалить: {failed}"
        return msg
    except Exception as e:
        return f"⚠️ Ошибка Taskdog: {e}"


def resolve_done(command):
    """Отметка 'сделано' по ID или позиции."""
    action = command.get("action")
    tasks = get_tasks_list()
    if not tasks:
        return "📭 Задач нет."

    if action in ("done_by_real_id", "done_by_id", "done_by_ordinal"):
        if action == "done_by_ordinal":
            idx = command["ordinal"]
            if idx == -1:
                idx = len(tasks)
            if idx < 1 or idx > len(tasks):
                return f"⚠️ Задачи №{idx} нет. Всего задач: {len(tasks)}."
            target = tasks[idx - 1]
        else:
            target_id = command["id"]
            target = next((t for t in tasks if t.get("id") == target_id), None)
            if not target:
                return f"⚠️ Задача [{target_id}] не найдена."
        name = target.get("name") or "задача"
        err = _patch_done(target["id"])
        if err != "ok":
            return err
        _log_completed(name, target["id"])
        return f"✅ Выполнено: [{target['id']}] — «{name}»"

    if action == "done_by_name":
        name_query = command["name"].lower()
        matches = [t for t in tasks if name_query in (t.get("name") or "").lower()]
        if not matches:
            return f"⚠️ Задача «{command['name']}» не найдена."
        if len(matches) > 1:
            lines = ["Найдено несколько, уточни ID:"]
            for m in matches:
                lines.append(f"  [{m['id']}] {m['name']}")
            return "\n".join(lines)
        target = matches[0]
        name = target.get("name") or "задача"
        err = _patch_done(target["id"])
        if err != "ok":
            return err
        _log_completed(name, target["id"])
        return f"✅ Выполнено: [{target['id']}] — «{name}»"

    return "⚠️ Не понял команду «сделал»."


def get_tasks_for_today():
    today = datetime.now().strftime("%Y-%m-%d")
    return [t for t in get_tasks_list() if (t.get("deadline") or "").startswith(today)]


def get_tasks_for_tomorrow():
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    return [t for t in get_tasks_list() if (t.get("deadline") or "").startswith(tomorrow)]


def get_overdue_tasks():
    today = datetime.now().strftime("%Y-%m-%d")
    return [
        t for t in get_tasks_list()
        if (t.get("deadline") or "") and t["deadline"][:10] < today
    ]


def get_tasks_without_deadline():
    return [t for t in get_tasks_list() if not t.get("deadline")]


def get_completed_today():
    today = datetime.now().strftime("%Y-%m-%d")
    return [d for d in _read_completed_log() if d.get("date") == today]


def list_all_tasks():
    """Все задачи: активные + выполненные."""
    active = get_tasks_list()
    completed = _read_completed_log()

    if not active and not completed:
        return "📭 Задач нет вообще."

    lines = []

    if active:
        lines.append(f"📋 Активные задачи ({len(active)}):")
        for t in active[:20]:
            name = t.get("name") or t.get("title") or "(без названия)"
            real_id = t.get("id", "?")
            tags = t.get("tags") or []
            prefix = "🔥 " if "важно" in tags else ""
            suffix_parts = []
            if t.get("deadline"):
                suffix_parts.append(f"до {_format_deadline(t['deadline'])}")
            suffix = f" ({', '.join(suffix_parts)})" if suffix_parts else ""
            lines.append(f"[{real_id}] {prefix}{name}{suffix}")
        if len(active) > 20:
            lines.append(f"  ... и ещё {len(active) - 20}")
        lines.append("")

    if completed:
        lines.append(f"✅ Выполнено всего ({len(completed)}):")
        recent = sorted(completed, key=lambda d: d.get("date", ""), reverse=True)[:20]
        for d in recent:
            date_str = d.get("date", "")
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                date_fmt = f"{dt.day:02d}.{dt.month:02d}.{dt.year}"
            except Exception:
                date_fmt = date_str
            lines.append(f"• {d.get('name', '?')} — {date_fmt}")
        if len(completed) > 20:
            lines.append(f"  ... и ещё {len(completed) - 20}")

    return "\n".join(lines)


def list_completed_month(year=None, month=None):
    """Выполненные за месяц (по умолчанию — текущий), по дням."""
    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    prefix = f"{year:04d}-{month:02d}"
    completed = [
        d for d in _read_completed_log()
        if (d.get("date") or "").startswith(prefix)
    ]

    month_name = f"{RU_MONTHS[month]} {year}"
    if not completed:
        return f"📭 За {month_name} выполненных задач нет."

    by_day = defaultdict(list)
    for d in completed:
        by_day[d.get("date")].append(d)

    lines = [f"✅ Выполнено за {month_name}: {len(completed)}", ""]

    for date_str in sorted(by_day.keys(), reverse=True):
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            day_label = f"{dt.day:02d} {RU_MONTHS_GEN[dt.month]}"
        except Exception:
            day_label = date_str
        lines.append(f"📅 {day_label}:")
        for d in by_day[date_str]:
            lines.append(f"  • {d.get('name', '?')} ({d.get('time', '')})")
        lines.append("")

    return "\n".join(lines).rstrip()


def list_completed_year(year=None):
    """Выполненные за год, по месяцам."""
    now = datetime.now()
    if year is None:
        year = now.year

    prefix = f"{year:04d}"
    completed = [
        d for d in _read_completed_log()
        if (d.get("date") or "").startswith(prefix)
    ]

    if not completed:
        return f"📭 За {year} год выполненных задач нет."

    by_month = defaultdict(list)
    for d in completed:
        try:
            m = int(d.get("date", "").split("-")[1])
            by_month[m].append(d)
        except Exception:
            continue

    lines = [f"✅ Выполнено за {year}: {len(completed)}", "", "📊 По месяцам:"]
    for m in sorted(by_month.keys()):
        lines.append(f"  • {RU_MONTHS[m]}: {len(by_month[m])}")
    lines.append("")

    recent = sorted(completed, key=lambda d: (d.get("date", ""), d.get("time", "")), reverse=True)[:10]
    lines.append("🕐 Последние выполненные:")
    for d in recent:
        date_str = d.get("date", "")
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            date_fmt = f"{dt.day:02d}.{dt.month:02d}"
        except Exception:
            date_fmt = date_str
        lines.append(f"  • {d.get('name', '?')} — {date_fmt}")

    return "\n".join(lines)


# ---------- Обёртки для обратной совместимости ----------

def delete_task(task_id):
    """Удалить по ID (обёртка)."""
    result = _delete_by_id(task_id)
    if result == "ok":
        return f"🗑️ Задача [{task_id}] удалена."
    return result


def mark_done_by_position(idx):
    """Отметить выполненной по позиции (для команды /done N)."""
    return resolve_done({"action": "done_by_ordinal", "ordinal": idx})


def mark_done(task_id):
    """Отметить выполненной по ID (обёртка)."""
    tasks = get_tasks_list()
    target = next((t for t in tasks if t.get("id") == task_id), None)
    if not target:
        return f"⚠️ Задача [{task_id}] не найдена."
    name = target.get("name") or "задача"
    err = _patch_done(task_id)
    if err != "ok":
        return err
    _log_completed(name, task_id)
    return f"✅ Выполнено: [{task_id}] — «{name}»"


def list_completed_tasks():
    """Показывает только выполненные задачи (без активных)."""
    completed = _read_completed_log()
    if not completed:
        return "📭 Выполненных задач нет."

    lines = [f"✅ Выполненные задачи ({len(completed)}):"]
    recent = sorted(
        completed,
        key=lambda d: (d.get("date", ""), d.get("time", "")),
        reverse=True,
    )
    for d in recent[:30]:
        date_str = d.get("date", "")
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            date_fmt = f"{dt.day:02d}.{dt.month:02d}"
        except Exception:
            date_fmt = date_str
        lines.append(f"• {d.get('name', '?')} — {date_fmt} {d.get('time', '')}")
    if len(completed) > 30:
        lines.append(f"  ... и ещё {len(completed) - 30}")
    return "\n".join(lines)


def undo_completed(position):
    """Возвращает задачу из выполненных в активные.

    position — номер в списке выполненных (1-based, по порядку из completed_log).
    Если задача ещё есть в Taskdog — возвращает статус в PENDING.
    Если её нет — создаёт заново.
    """
    log = _read_completed_log()
    if not log:
        return "📭 Список выполненных пуст."

    # Сортируем так же, как в list_completed_tasks — свежие сверху
    sorted_log = sorted(
        log,
        key=lambda d: (d.get("date", ""), d.get("time", "")),
        reverse=True,
    )

    if position < 1 or position > len(sorted_log):
        return f"⚠️ В выполненных только {len(sorted_log)} задач."

    entry = sorted_log[position - 1]
    name = entry.get("name", "?")
    old_id = entry.get("id")

    # Проверяем, есть ли задача среди активных
    active = get_tasks_list()
    in_active = next((t for t in active if t.get("id") == old_id), None)

    action_taken = ""

    if in_active:
        # Задача ещё жива — возвращаем статус в PENDING через PATCH
        try:
            r = httpx.patch(
                f"{TASKDOG_API_URL}/api/v1/tasks/{old_id}",
                json={"status": "PENDING"},
                headers=HEADERS,
                timeout=10,
                follow_redirects=True,
            )
            if r.status_code < 400:
                action_taken = f"статус возвращён в PENDING (ID={old_id})"
            else:
                action_taken = f"⚠️ PATCH вернул {r.status_code}, но задача была в активных"
        except Exception as e:
            action_taken = f"⚠️ Ошибка PATCH: {e}"
    else:
        # Задачи нет — создаём заново
        try:
            r = httpx.post(
                f"{TASKDOG_API_URL}/api/v1/tasks",
                json={"name": name, "priority": 5},
                headers=HEADERS,
                timeout=10,
                follow_redirects=True,
            )
            r.raise_for_status()
            new_task = r.json()
            new_id = new_task.get("id")
            action_taken = f"создана заново (новый ID={new_id})"
        except Exception as e:
            return f"⚠️ Не удалось создать задачу: {e}"

    # Убираем из лога выполненных
    new_log = [
        d for d in log
        if not (d.get("id") == old_id
                and d.get("name") == name
                and d.get("date") == entry.get("date")
                and d.get("time") == entry.get("time"))
    ]
    with open(COMPLETED_LOG, "w") as f:
        json.dump(new_log, f, ensure_ascii=False, indent=2)

    return f"↩️ Задача «{name}» возвращена в активные ({action_taken})."


def list_completed_today():
    """Показывает выполненные за сегодня."""
    today = datetime.now().strftime("%Y-%m-%d")
    completed = [d for d in _read_completed_log() if d.get("date") == today]

    if not completed:
        return "📭 Сегодня ещё ничего не выполнено."

    lines = [f"✅ Выполнено за сегодня ({len(completed)}):"]
    sorted_log = sorted(completed, key=lambda d: d.get("time", ""), reverse=True)
    for d in sorted_log:
        lines.append(f"• {d.get('name', '?')} — {d.get('time', '')}")
    return "\n".join(lines)
