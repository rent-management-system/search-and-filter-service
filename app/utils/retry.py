import asyncio
from functools import wraps
import structlog

logger = structlog.get_logger()

def retry(tries: int = 3, delay: float = 1, backoff: float = 2):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 1
            current_delay = delay
            while attempt <= tries:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    logger.warning("Retry attempt failed", func=func.__name__, attempt=attempt, error=str(e))
                    if attempt == tries:
                        raise
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
                    attempt += 1
        return wrapper
    return decorator
