import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
GOOGLE_TOKEN_FILE = os.getenv("GOOGLE_TOKEN_FILE", "token.json")
LOG_FILE = os.getenv("LOG_FILE", "data/syrcode_log.txt")



# Taskdog
TASKDOG_API_URL = os.getenv("TASKDOG_API_URL", "http://127.0.0.1:8100")
TASKDOG_API_KEY = os.getenv("TASKDOG_API_KEY", "")

# OpenRouter
WHISPER_URL = os.getenv("WHISPER_URL", "http://127.0.0.1:8080")

# GigaChat
GIGACHAT_AUTH_KEY = os.getenv("GIGACHAT_AUTH_KEY", "")

# GigaChat
GIGACHAT_AUTH_KEY = os.getenv('GIGACHAT_AUTH_KEY', '')
GIGACHAT_PROXY = os.getenv('GIGACHAT_PROXY', '')
