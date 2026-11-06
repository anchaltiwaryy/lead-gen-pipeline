"""Tiered cache-aside engine: Redis (Upstash/local) -> SQLite `kv_cache` fallback.

Layer 1: Redis for sub-2ms cross-instance lookups.
Layer 2: Local SQLite `kv_cache` table (created by db.py) when Redis is
         offline or unconfigured -> zero-dependency local caching.

TTL Policies (see AGENTS.md):
  - LLM prompts/responses:   14 days (keyed on sha256(system + user prompt))
  - Web domain scrapes:       7 days (keyed on domain hash)
  - SMTP deliverability/MX:  30 days (keyed on mx_host)

Decorators:
  @cached_llm(ttl=...), @cached_scrape(ttl=...), @cached_smtp(ttl=...)
"""
import hashlib
import json
import os
import time
from functools import wraps

from db import get_conn, db_cache_get, db_cache_set, db_cache_delete

REDIS_URL = os.getenv("REDIS_URL", "")

# Default TTLs (seconds)
LLM_TTL = 1209600       # 14 days
SCRAPE_TTL = 604800     # 7 days
SMTP_TTL = 2592000      # 30 days


def _connect_redis(redis_url: str):
    if not redis_url:
        return None
    try:
        import redis
        client = redis.Redis.from_url(
            redis_url,
            socket_timeout=0.5,
            socket_connect_timeout=0.5,
        )
        client.ping()
        return client
    except Exception:
        return None


class CacheClient:
    """Unified get/set/delete over Redis with automatic SQLite fallback."""

    def __init__(self, redis_url: str = ""):
        self._redis = _connect_redis(redis_url)

    @property
    def backend(self) -> str:
        return "redis" if self._redis is not None else "sqlite"

    def get(self, key: str):
        """Return cached string/JSON value or None on miss."""
        if self._redis is not None:
            try:
                raw = self._redis.get(key)
                if raw is not None:
                    return raw.decode("utf-8")
            except Exception:
                self._redis = None  # degrade to SQLite for the rest of the run
        conn = get_conn()
        try:
            return db_cache_get(conn, key)
        finally:
            conn.close()

    def set(self, key: str, value: str, ttl_seconds: int = LLM_TTL) -> None:
        if self._redis is not None:
            try:
                self._redis.set(key, value, ex=ttl_seconds)
                return
            except Exception:
                self._redis = None
        conn = get_conn()
        try:
            db_cache_set(conn, key, value, ttl_seconds)
        finally:
            conn.close()

    def delete(self, key: str) -> None:
        if self._redis is not None:
            try:
                self._redis.delete(key)
            except Exception:
                self._redis = None
        conn = get_conn()
        try:
            db_cache_delete(conn, key)
        finally:
            conn.close()

    def clear(self) -> None:
        """Purge all entries from the active backend (best-effort)."""
        if self._redis is not None:
            try:
                self._redis.flushdb()
            except Exception:
                self._redis = None
        conn = get_conn()
        try:
            conn.execute("DELETE FROM kv_cache")
            conn.commit()
        finally:
            conn.close()


# --- Key derivation -------------------------------------------------------

def _hash(*parts) -> str:
    raw = "\n".join(str(p) for p in parts if p is not None)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _llm_key(args, kwargs) -> str:
    """Key on sha256(system_prompt + user_prompt)."""
    system = kwargs.get("system_prompt") or kwargs.get("system") or (args[0] if args else "")
    user = kwargs.get("user_prompt") or kwargs.get("user") or (args[1] if len(args) > 1 else "")
    return _hash(system, user)


def _domain_key(args, kwargs) -> str:
    domain = kwargs.get("domain") or kwargs.get("url") or kwargs.get("company_domain") \
        or (args[0] if args else "")
    return _hash(domain)


def _mx_key(args, kwargs) -> str:
    mx = kwargs.get("mx_host") or kwargs.get("mx") or (args[0] if args else "")
    return _hash(mx)


# --- Value codec ----------------------------------------------------------

def _encode(value) -> str:
    if isinstance(value, str):
        return json.dumps({"t": "s", "v": value})
    return json.dumps({"t": "j", "v": value}, default=str)


def _decode(raw: str):
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "t" in data:
            return data["v"]
        return data
    except Exception:
        return raw


# --- Decorators -----------------------------------------------------------

_client = CacheClient(REDIS_URL)


def cached(prefix: str, ttl: int, key_builder, client: CacheClient | None = None):
    """Generic cache-aside decorator. Serializes str passthrough, else JSON."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = f"{prefix}:{key_builder(args, kwargs)}"
            cache = client or _client
            cached_value = cache.get(key)
            if cached_value is not None:
                return _decode(cached_value)
            result = func(*args, **kwargs)
            cache.set(key, _encode(result), ttl)
            return result
        return wrapper
    return decorator


def cached_llm(ttl: int = LLM_TTL, client: CacheClient | None = None):
    """14-day cache keyed on sha256(system_prompt + user_prompt)."""
    return cached("llm", ttl, _llm_key, client)


def cached_scrape(ttl: int = SCRAPE_TTL, client: CacheClient | None = None):
    """7-day cache keyed on domain hash."""
    return cached("scrape", ttl, _domain_key, client)


def cached_smtp(ttl: int = SMTP_TTL, client: CacheClient | None = None):
    """30-day cache keyed on mx_host (SMTP deliverability results)."""
    return cached("smtp", ttl, _mx_key, client)


def flush_expired() -> int:
    """Purge expired SQLite cache rows; returns rows deleted."""
    conn = get_conn()
    try:
        cur = conn.execute("DELETE FROM kv_cache WHERE expires_at <= ?", (time.time(),))
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()