#!/usr/bin/env python3
"""Отправка бэкапа СырКода в Telegram через SOCKS5-прокси."""
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import httpx

HOME = Path.home()
BACKUP_DIR = HOME / "full-backups"
ENV_FILE = HOME / "syrcode-bot" / ".env"
CHAT_ID_FILE = HOME / "syrcode-bot" / "data" / "chat_id.txt"
PROXY = "socks5://127.0.0.1:1443"


def run_backup():
    print(">>> 1. Делаем бэкап...")
    r = subprocess.run(
        ["bash", "-c", f'echo "" | {HOME}/full_backup.sh'],
        capture_output=True, text=True, timeout=300,
    )
    if r.returncode != 0:
        print("❌ Ошибка бэкапа:")
        print(r.stdout[-1000:])
        print(r.stderr[-1000:])
        sys.exit(1)
    print("   ✅ Бэкап создан")


def find_latest_archive():
    files = sorted(
        BACKUP_DIR.glob("syrcode_full_*"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not files:
        print(f"❌ Нет архивов в {BACKUP_DIR}")
        sys.exit(1)
    return files[0]


def read_env_token():
    content = ENV_FILE.read_text()
    m = re.search(r"^TELEGRAM_BOT_TOKEN=(.+)$", content, re.MULTILINE)
    if not m:
        print("❌ TELEGRAM_BOT_TOKEN не найден в .env")
        sys.exit(1)
    return m.group(1).strip()


def read_chat_id():
    try:
        return CHAT_ID_FILE.read_text().strip()
    except Exception:
        print(f"❌ Не могу прочитать chat_id из {CHAT_ID_FILE}")
        sys.exit(1)


def send_to_telegram(token, chat_id, archive):
    size_kb = archive.stat().st_size // 1024
    caption = f"📦 Автобэкап {datetime.now().strftime('%d.%m.%Y %H:%M')} • {size_kb} КБ"

    print(f">>> 3. Отправляем в Telegram (chat_id: {chat_id})...")
    url = f"https://api.telegram.org/bot{token}/sendDocument"

    with open(archive, "rb") as f:
        files = {"document": (archive.name, f, "application/gzip")}
        data = {"chat_id": chat_id, "caption": caption}

        with httpx.Client(proxy=PROXY, timeout=180) as client:
            r = client.post(url, data=data, files=files)

    if r.status_code == 200 and r.json().get("ok"):
        print("   ✅ Отправлено в Telegram")
        return True
    else:
        print(f"   ❌ Ошибка: HTTP {r.status_code}")
        print(f"   {r.text[:400]}")
        return False


def main():
    run_backup()
    archive = find_latest_archive()
    size_kb = archive.stat().st_size // 1024
    print(f">>> 2. Архив: {archive} ({size_kb} КБ)")

    token = read_env_token()
    chat_id = read_chat_id()

    if not send_to_telegram(token, chat_id, archive):
        sys.exit(1)


if __name__ == "__main__":
    main()
