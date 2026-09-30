from openai import OpenAI

from app.configs import settings

openai_client = OpenAI(
    api_key=settings.MODEL_API_KEY,
    base_url=settings.MODEL_BASE_URL,
)
