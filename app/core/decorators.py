import functools
import logging
import time
from typing import Tuple, Type

logger = logging.getLogger(__name__)


def with_retry(
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    max_retries: int = 3,
    base_delay: float = 1.0,
):
    """Decorator that retries the wrapped function with exponential backoff.

    Args:
        retryable_exceptions: Exception types that should trigger a retry.
        max_retries: Maximum number of attempts before re-raising.
        base_delay: Initial wait in seconds; doubles on each subsequent attempt.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as exc:
                    wait = base_delay * (2**attempt)
                    if attempt < max_retries - 1:
                        logger.warning(
                            "%s failed (attempt %d/%d): %s. Retrying in %.1fs.",
                            func.__name__,
                            attempt + 1,
                            max_retries,
                            exc,
                            wait,
                        )
                        time.sleep(wait)
                    else:
                        logger.error(
                            "%s failed after %d attempts: %s",
                            func.__name__,
                            max_retries,
                            exc,
                        )
                        raise

        return wrapper

    return decorator
