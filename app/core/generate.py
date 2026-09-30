from typing import List

import openai

from app.configs import settings
from app.core.client import openai_client
from app.core.decorators import with_retry


@with_retry(
    retryable_exceptions=(openai.RateLimitError, openai.APIError),
    max_retries=3,
    base_delay=1.0,
)
def generate_embedding(text: str, dimensions: int = 768) -> List[float]:
    response = openai_client.embeddings.create(
        model=settings.MODEL_EMBEDDING_NAME,
        input=text,
        dimensions=dimensions,
    )

    return response.data[0].embedding
