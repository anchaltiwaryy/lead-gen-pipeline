"""Resilience utility for LLM API calls with exponential backoff + jitter."""
import time
import random
import functools
import logging

logger = logging.getLogger("pipeline")


def with_retry(max_retries: int = 5, initial_delay: float = 1.5, max_delay: float = 20.0, backoff_factor: float = 2.0):
    """Decorator to retry flaky or rate-limited API calls (HTTP 429, 503, etc.)."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    err_msg = str(e).lower()
                    is_rate_limit = any(k in err_msg for k in ["rate limit", "429", "quota", "too many requests", "503", "unavailable", "timeout"])
                    
                    if attempt == max_retries or not is_rate_limit:
                        logger.error(f"[API Error] {func.__name__} failed on attempt {attempt}/{max_retries}: {e}")
                        raise e
                    
                    # Add jitter
                    sleep_time = min(max_delay, delay * (1 + random.uniform(0.1, 0.4)))
                    logger.warning(f"[API Retry] {func.__name__} hit rate limit / transient error on attempt {attempt}. Retrying in {sleep_time:.2f}s... Error: {e}")
                    time.sleep(sleep_time)
                    delay *= backoff_factor
            return func(*args, **kwargs)
        return wrapper
    return decorator
