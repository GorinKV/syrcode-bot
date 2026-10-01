from openai import AsyncOpenAI
from config import LLM_BASE_URL, LLM_MODEL
from core.gigachat_auth import get_access_token, reset_token


SYSTEM_PROMPT = """Ты — СырКод, личный ассистент сыровара, блогера и Python-разработчика.
Твои задачи:
- помогать собирать и развивать идеи (сыр, блог, код, бизнес);
- придумывать темы и черновики постов для блога сыровара;
- объяснять Python, помогать с Git и кодом;
- отвечать кратко, по делу, без воды.

Если пользователь просит создать задачу — подскажи ему использовать команду /task Название.
Отвечай на русском языке."""


async def _call_gigachat(token: str, user_message: str) -> str:
    client = AsyncOpenAI(base_url=LLM_BASE_URL, api_key=token)
    response = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.7,
        max_tokens=700,
    )
    return response.choices[0].message.content


async def ask_llm(user_message: str) -> str:
    try:
        token = await get_access_token()
    except Exception as e:
        return f"⚠️ Не удалось получить токен GigaChat: {e}"

    try:
        return await _call_gigachat(token, user_message)
    except Exception as e:
        err_text = str(e)
        is_auth_error = (
            "401" in err_text
            or "expired" in err_text.lower()
            or "unauthorized" in err_text.lower()
        )
        if is_auth_error:
            print(">>> [orchestrator] Токен отвергнут (401), обновляем...")
            reset_token()
            try:
                fresh = await get_access_token()
                return await _call_gigachat(fresh, user_message)
            except Exception as e2:
                return f"⚠️ Ошибка GigaChat (после обновления токена): {e2}"
        return f"⚠️ Ошибка GigaChat: {e}"
