import httpx
from openai import AsyncOpenAI
from config import LLM_BASE_URL, LLM_MODEL, GIGACHAT_PROXY
from core.gigachat_auth import get_access_token

SYSTEM_PROMPT = """Ты — СырКод, личный ассистент сыровара, блогера и Python-разработчика.
Твои задачи:
- помогать собирать и развивать идеи (сыр, блог, код, бизнес);
- придумывать темы и черновики постов для блога сыровара;
- объяснять Python, помогать с Git и кодом;
- отвечать кратко, по делу, без воды.

Если пользователь просит создать задачу — подскажи ему использовать команду /task Название.
Отвечай на русском языке."""


async def ask_llm(user_message: str) -> str:
    try:
        token = await get_access_token()
        kwargs = {"verify": False, "timeout": 60}
        if GIGACHAT_PROXY:
            kwargs["proxy"] = GIGACHAT_PROXY
        http_client = httpx.AsyncClient(**kwargs)
        client = AsyncOpenAI(
            base_url=LLM_BASE_URL,
            api_key=token,
            http_client=http_client,
        )
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.7,
            max_tokens=700,
        )
        await http_client.aclose()
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ Ошибка GigaChat: {e}"
