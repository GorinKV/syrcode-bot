import httpx
from config import WHISPER_URL


async def transcribe_voice(file_bytes: bytes, filename: str = "voice.ogg") -> str:
    """Распознаёт речь через локальный whisper.cpp сервер."""
    try:
        files = {"file": (filename, file_bytes, "audio/ogg")}
        data = {"language": "ru", "response_format": "json"}

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{WHISPER_URL}/inference",
                files=files,
                data=data,
            )
            response.raise_for_status()
            result = response.json()
            return result.get("text", "").strip()
    except Exception as e:
        return f"__ERROR__: Ошибка распознавания: {e}"


def extract_command(text: str) -> dict:
    """Извлекает команду из распознанного текста."""
    text_lower = text.lower().strip()

    VOICE_COMMANDS = {
        "новая идея": "idea",
        "запиши идею": "idea",
        "идея": "idea",
        "позвонить": "task_call",
        "написать": "task_write",
        "встретиться": "task_meet",
        "сделать": "task_do",
        "новая задача": "task",
        "задача": "task",
        "купить": "task_buy",
    }

    for phrase, cmd_type in VOICE_COMMANDS.items():
        if text_lower.startswith(phrase):
            remainder = text[len(phrase):].strip(" ,.:;!?")
            return {"type": cmd_type, "text": remainder or ""}

    action_verbs = ["позвони", "напиши", "встреться", "сделай", "купи", "запиши"]
    for verb in action_verbs:
        if text_lower.startswith(verb):
            remainder = text[len(verb):].strip(" ,.:;!?")
            if remainder:
                return {"type": "task", "text": remainder}

    return {"type": "none", "text": text}
