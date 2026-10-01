"""Универсальный парсер естественных команд. Устойчив к искажениям."""
import re
from core.date_parser import parse_deadline, parse_important

ORDINALS = {
    "перв": 1, "втор": 2, "треть": 3, "четвёрт": 4, "четверт": 4,
    "пят": 5, "шест": 6, "седьм": 7, "восьм": 8, "девят": 9, "десят": 10,
    "последн": -1,
}

DELETE_VERBS = ("удали", "удалить", "убери", "убрать", "снеси", "стереть", "delete")
LIST_VERBS = ("покажи", "список", "перечисли", "какие", "что за", "show", "list", "все")
IDEA_VERBS = ("идея", "запиши идею", "новая идея", "сохрани идею", "запомни идею")
HELP_VERBS = ("помощь", "команды", "что ты умеешь", "help")
DONE_VERBS = ("сделал", "сделала", "выполнил", "выполнила", "готово", "закрыл", "закрыла", "done")

TASK_TRIGGERS_ANYWHERE = (
    "задач", "надо", "нужно", "напомни", "запланируй",
    "сделай", "сделать", "добавь",
    "важно", "срочно", "обязательно", "приоритетно",
)

ACTION_VERBS = {
    "позвон": "Позвонить", "позвони": "Позвонить", "набра": "Позвонить",
    "напи": "Написать", "написа": "Написать", "ответ": "Ответить", "отправ": "Отправить",
    "встрет": "Встретиться", "куп": "Купить", "закаж": "Заказать", "заказа": "Заказать",
    "забер": "Забрать", "сдела": "Сделать", "провер": "Проверить", "поздрав": "Поздравить",
    "свари": "Сварить", "сварит": "Сварить", "приготов": "Приготовить",
    "почин": "Починить", "постир": "Постирать", "поглад": "Погладить",
    "посмотр": "Посмотреть", "почит": "Почитать", "поех": "Поехать",
    "сход": "Сходить", "погул": "Погулять",
}

FUZZY_FIXES = {
    "садач": "задач", "задачч": "задач", "зодач": "задач",
    "позван": "позвон", "пазвон": "позвон", "нозвон": "позвон",
    "нописа": "написа", "нописат": "написать",
    "купт": "купить", "купит": "купить",
    "встретт": "встрет", "удал": "удали", "идеяя": "идея",
}


def _normalize(text):
    t = text.lower()
    for wrong, right in FUZZY_FIXES.items():
        t = re.sub(rf"\b{wrong}", right, t)
    return t


def _strip_trigger_prefix(text, triggers):
    for tr in triggers:
        pattern = rf"^{tr}\w*\s*[—:\-]?\s*"
        new = re.sub(pattern, "", text, count=1, flags=re.I).strip()
        if new != text:
            return new
    return text


def _extract_action_title(text):
    t = _normalize(text)
    earliest_pos = len(t)
    earliest_kind = None
    earliest_len = 0
    for stem, kind in ACTION_VERBS.items():
        pos = t.find(stem)
        if pos != -1 and pos < earliest_pos:
            earliest_pos = pos
            earliest_kind = kind
            m = re.match(rf"{re.escape(stem)}\w*", t[pos:])
            earliest_len = len(m.group(0)) if m else len(stem)
    if earliest_kind is None:
        return None, text
    after_start = earliest_pos + earliest_len
    after = text[after_start:].strip(" ,.:;!?—-\t")
    return earliest_kind, after


def parse(text):
    original = text.strip()
    t = _normalize(original)
    t_stripped = t.strip()

    # --- Короткие фразы (день / месяц / год) ---
    if t_stripped in ("за день", "день", "за сегодня", "сегодня", "за этот день"):
        return {"action": "list_completed_today"}
    if t_stripped in ("за месяц", "месяц", "за этот месяц", "этот месяц", "в этом месяце"):
        return {"action": "list_completed_month"}
    if t_stripped in ("за год", "год", "за этот год", "этот год", "в этом году"):
        return {"action": "list_completed_year"}

    # --- Помощь ---
    if any(v in t for v in HELP_VERBS) and len(t) < 40:
        return {"action": "help"}

    # --- ВАЖНО: "сделал/выполнил" ПЕРЕД историей ---
    if any(t.startswith(v) for v in DONE_VERBS):
        # Порядковое слово: "выполнил вторую"
        for prefix, idx in ORDINALS.items():
            if prefix in t:
                return {"action": "done_by_ordinal", "ordinal": idx}
        # ID: "#3", "id 3"
        m = re.search(r"(?:#|\bid\s*[:№]?\s*)(\d+)", t)
        if m:
            return {"action": "done_by_id", "id": int(m.group(1))}
        # Просто число: "выполнил 4"
        m = re.search(r"(\d+)", t)
        if m:
            return {"action": "done_by_id", "id": int(m.group(1))}
        # По имени
        rest = original
        for v in DONE_VERBS:
            rest = re.sub(rf"^{v}\w*\s+", "", rest, flags=re.I)
        rest = rest.strip(" .,!?:;")
        if rest:
            return {"action": "done_by_name", "name": rest}
        return {"action": "none"}

    # --- История: "выполненные за месяц/год" (только если не глагол действия) ---
    if "выполн" in t or "сдела" in t or "закрыт" in t:
        if "месяц" in t:
            return {"action": "list_completed_month"}
        if "год" in t:
            return {"action": "list_completed_year"}
        if any(w in t for w in ("задач", "список", "покажи", "все")) or t.strip() in (
            "выполненные", "выполнено", "сделанные", "сделано"
        ):
            return {"action": "list_completed"}

    # --- Удаление ---
    is_delete = any(t.startswith(v) or f" {v} " in f" {t} " for v in DELETE_VERBS)
    if is_delete:
        if re.search(r"\bвсе\b.*\bзадач", t) or "очисти" in t or "очистить" in t:
            return {"action": "clear_all"}
        m = re.search(r"(?:#|\bid\s*[:№]?\s*|задач[ауи]?\s*№?\s*)(\d+)", t)
        if m:
            return {"action": "delete_by_real_id", "id": int(m.group(1))}
        m = re.search(r"^удали\w*\s+(\d+)\s*$", t)
        if m:
            return {"action": "delete_by_real_id", "id": int(m.group(1))}
        for prefix, idx in ORDINALS.items():
            if prefix in t:
                return {"action": "delete_by_ordinal", "ordinal": idx}
        rest = original
        for v in DELETE_VERBS:
            rest = re.sub(rf"^{v}\w*\s+", "", rest, flags=re.I)
        rest = re.sub(r"^задач[ауи]?\s+", "", rest, flags=re.I).strip(" .,!?:;")
        if rest:
            return {"action": "delete_by_name", "name": rest}
        return {"action": "none"}

    # --- Все задачи ---
    if "все" in t and ("задач" in t or "дел" in t):
        if "выполн" not in t and "сдела" not in t:
            return {"action": "list_all"}

    # --- Список активных ---
    if any(v in t for v in LIST_VERBS) and any(w in t for w in ("задач", "дел", "task")):
        return {"action": "list_tasks"}

    # --- Идея ---
    for v in IDEA_VERBS:
        if t.startswith(v) or f" {v}" in t:
            text_after = re.sub(
                rf"^.*?{v}\w*\s*[—:\-]?\s*", "", original, count=1, flags=re.I
            ).strip()
            return {"action": "add_idea", "text": text_after}

    # --- Создание задачи ---
    has_task_trigger = any(tr in t for tr in TASK_TRIGGERS_ANYWHERE)
    starts_with_action = any(re.match(rf"{stem}", t) for stem in ACTION_VERBS)
    if not has_task_trigger and not starts_with_action:
        return {"action": "none"}

    kind, after = _extract_action_title(t)
    if kind is not None:
        after = after.strip()
        after = re.sub(r"^задач[ауи]?\s*", "", after, flags=re.I).strip()
        title_core = after if after else ""
        important_full, _ = parse_important(original)
        deadline_full, _ = parse_deadline(original)
        deadline, title_core = parse_deadline(title_core)
        important, title_core = parse_important(title_core)
        important = important or important_full
        deadline = deadline or deadline_full
        full_title = f"{kind} {title_core}".strip() if title_core else kind
        return {
            "action": "add_task",
            "title": full_title,
            "deadline": deadline,
            "important": important,
        }

    rest = _strip_trigger_prefix(original, TASK_TRIGGERS_ANYWHERE)
    if rest:
        deadline, rest = parse_deadline(rest)
        important, rest = parse_important(rest)
        if rest:
            return {
                "action": "add_task",
                "title": rest,
                "deadline": deadline,
                "important": important,
            }

    return {"action": "none"}
