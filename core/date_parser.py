"""Парсер дат и важности из естественного языка."""
import re
from datetime import datetime, timedelta


WEEKDAYS = {
    "понедельник": 0, "понедельника": 0, "понедельнику": 0,
    "вторник": 1, "вторника": 1, "вторнику": 1,
    "среда": 2, "среду": 2, "среды": 2, "среде": 2,
    "четверг": 3, "четверга": 3, "четвергу": 3,
    "пятница": 4, "пятницу": 4, "пятницы": 4, "пятнице": 4,
    "суббота": 5, "субботу": 5, "субботы": 5, "субботе": 5,
    "воскресенье": 6, "воскресенье": 6, "воскресенья": 6, "воскресенью": 6,
}

MONTHS = {
    "января": 1, "январь": 1,
    "февраля": 2, "февраль": 2,
    "марта": 3, "март": 3,
    "апреля": 4, "апрель": 4,
    "мая": 5, "май": 5,
    "июня": 6, "июнь": 6,
    "июля": 7, "июль": 7,
    "августа": 8, "август": 8,
    "сентября": 9, "сентябрь": 9,
    "октября": 10, "октябрь": 10,
    "ноября": 11, "ноябрь": 11,
    "декабря": 12, "декабрь": 12,
}

# Ключевые слова важности
IMPORTANT_WORDS = ("важно", "срочно", "важное", "приоритетно", "обязательно")

# Слова-связки для дат
DATE_PREFIXES = ("до", "к", "на", "в", "во")


def _next_weekday(target_wd: int) -> datetime:
    """Ближайший следующий указанный день недели."""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    current_wd = today.weekday()
    delta = (target_wd - current_wd) % 7
    if delta == 0:
        delta = 7
    return today + timedelta(days=delta)


def parse_deadline(text: str) -> tuple[str | None, str]:
    """
    Ищет в тексте срок. Возвращает (iso_дата или None, текст без срока).
    """
    original = text
    t = text.lower()
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    deadline = None
    matched_phrase = ""

    # "послезавтра"
    if "послезавтра" in t:
        deadline = today + timedelta(days=2)
        matched_phrase = "послезавтра"
    # "завтра"
    elif "завтра" in t:
        deadline = today + timedelta(days=1)
        matched_phrase = "завтра"
    # "сегодня"
    elif "сегодня" in t:
        deadline = today
        matched_phrase = "сегодня"
    # "через N дней/недель/месяцев"
    elif (m := re.search(r"через\s+(\d+)\s+(день|дня|дней)", t)):
        deadline = today + timedelta(days=int(m.group(1)))
        matched_phrase = m.group(0)
    elif (m := re.search(r"через\s+(\d+)\s+(неделю|недели|недель)", t)):
        deadline = today + timedelta(weeks=int(m.group(1)))
        matched_phrase = m.group(0)
    elif (m := re.search(r"через\s+(\d+)\s+(месяц|месяца|месяцев)", t)):
        deadline = today + timedelta(days=30 * int(m.group(1)))
        matched_phrase = m.group(0)
    elif "через неделю" in t:
        deadline = today + timedelta(weeks=1)
        matched_phrase = "через неделю"
    elif "через месяц" in t:
        deadline = today + timedelta(days=30)
        matched_phrase = "через месяц"
    # "15 октября" / "15 октября 2026"
    elif (m := re.search(r"(\d{1,2})\s+([а-яё]+)(?:\s+(\d{4}))?", t)):
        day = int(m.group(1))
        month_name = m.group(2)
        year = int(m.group(3)) if m.group(3) else None
        if month_name in MONTHS:
            month = MONTHS[month_name]
            if year is None:
                year = today.year
                candidate = datetime(year, month, day)
                if candidate < today:
                    candidate = datetime(year + 1, month, day)
            else:
                candidate = datetime(year, month, day)
            deadline = candidate
            matched_phrase = m.group(0)
    # "15.10" / "15.10.2026"
    elif (m := re.search(r"(\d{1,2})[.\-/](\d{1,2})(?:[.\-/](\d{2,4}))?", t)):
        day = int(m.group(1))
        month = int(m.group(2))
        year_str = m.group(3)
        if 1 <= day <= 31 and 1 <= month <= 12:
            if year_str:
                year = int(year_str)
                if year < 100:
                    year += 2000
            else:
                year = today.year
                candidate = datetime(year, month, day)
                if candidate < today:
                    candidate = datetime(year + 1, month, day)
            deadline = datetime(year, month, day) if year_str else candidate
            matched_phrase = m.group(0)
    # "в пятницу", "к пятнице", "до среды"
    else:
        for wd_name, wd_num in WEEKDAYS.items():
            if wd_name in t:
                deadline = _next_weekday(wd_num)
                # Находим полную фразу с предлогом
                for prefix in DATE_PREFIXES:
                    if f"{prefix} {wd_name}" in t:
                        matched_phrase = f"{prefix} {wd_name}"
                        break
                if not matched_phrase:
                    matched_phrase = wd_name
                break

    if deadline is None:
        return None, original

    iso = deadline.strftime("%Y-%m-%dT%H:%M:%S")
    # Убираем найденную фразу из текста
    cleaned = re.sub(rf"\b{re.escape(matched_phrase)}\b", "", original, count=1, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.:;!?—-\t")
    return iso, cleaned


def parse_important(text: str) -> tuple[bool, str]:
    """Ищет слова важности. Возвращает (bool, текст без них)."""
    t = text.lower()
    original = text
    found = False
    for w in IMPORTANT_WORDS:
        if re.search(rf"\b{w}\b", t):
            found = True
            original = re.sub(rf"\b{w}\b", "", original, count=1, flags=re.I)
    if found:
        original = re.sub(r"\s+", " ", original).strip(" ,.:;!?—-\t")
    return found, original
