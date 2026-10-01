import datetime
import os
from config import LOG_FILE


def log_to_file(user_message: str, bot_response: str):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] Вы: {user_message}\n")
        f.write(f"[{timestamp}] СырКод: {bot_response}\n\n")
