import time
import asyncio
import uuid
import httpx
from config import GIGACHAT_AUTH_KEY, GIGACHAT_PROXY

OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
SCOPE = "GIGACHAT_API_PERS"

_access_token = None
_expires_at = 0.0
_lock = asyncio.Lock()


async def get_access_token() -> str:
    global _access_token, _expires_at
    async with _lock:
        if _access_token and time.time() < _expires_at - 60:
            return _access_token
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(uuid.uuid4()),
            "Authorization": f"Basic {GIGACHAT_AUTH_KEY}",
        }
        data = {"scope": SCOPE}
        kwargs = {"timeout": 15, "verify": False, "follow_redirects": True}
        if GIGACHAT_PROXY:
            kwargs["proxy"] = GIGACHAT_PROXY
        async with httpx.AsyncClient(**kwargs) as client:
            response = await client.post(OAUTH_URL, headers=headers, data=data)
            response.raise_for_status()
            payload = response.json()
        _access_token = payload["access_token"]
        _expires_at = payload.get("expires_at", time.time() + 1800)
        print(f">>> GigaChat: токен обновлён, действует до {time.strftime('%H:%M:%S', time.localtime(_expires_at))}")
        return _access_token


def reset_token():
    """Сбрасывает кэшированный токен — следующий get_access_token запросит новый."""
    global _access_token, _expires_at
    _access_token = None
    _expires_at = 0.0
    print(">>> GigaChat: токен сброшен (reset_token)")
