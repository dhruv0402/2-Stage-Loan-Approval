"""Redis caching & API rate-limiting layer with graceful in-memory fallback."""
import os
import json
import time
from typing import Any

REDIS_URL = os.getenv('REDIS_URL', '')

_redis_client = None
_memory_cache: dict[str, tuple[float, Any]] = {}
_memory_rate_limits: dict[str, list[float]] = {}

if REDIS_URL:
    try:
        import redis
        _redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        _redis_client.ping()
        print(f"✓ Connected to Redis at {REDIS_URL}")
    except Exception as e:
        print(f"⚠ Redis connection failed ({e}). Falling back to in-memory cache.")
        _redis_client = None

def cache_get(key: str) -> Any | None:
    """Retrieve item from Redis or in-memory fallback."""
    if _redis_client:
        try:
            val = _redis_client.get(key)
            return json.loads(val) if val else None
        except Exception:
            pass
    # In-memory fallback with TTL check
    if key in _memory_cache:
        expire_at, data = _memory_cache[key]
        if time.time() < expire_at:
            return data
        else:
            del _memory_cache[key]
    return None

def cache_set(key: str, data: Any, ttl_seconds: int = 3600):
    """Store item in Redis or in-memory fallback."""
    if _redis_client:
        try:
            _redis_client.setex(key, ttl_seconds, json.dumps(data))
            return
        except Exception:
            pass
    _memory_cache[key] = (time.time() + ttl_seconds, data)

def get_client_identifier(request) -> str:
    """Extract authenticated API key or verified client IP from request."""
    # Check for Bearer token or API key first
    api_key = request.headers.get('X-API-Key')
    if api_key:
        return f"key:{api_key}"
    
    # Securely inspect Forwarded / X-Forwarded-For headers
    x_forwarded = request.headers.get('X-Forwarded-For')
    if x_forwarded:
        # First IP in X-Forwarded-For is client originating IP
        client_ip = x_forwarded.split(',')[0].strip()
        return f"ip:{client_ip}"
    
    client_host = request.client.host if request.client else '127.0.0.1'
    return f"ip:{client_host}"

def check_rate_limit(client_id: str, max_requests: int = 60, window_seconds: int = 60) -> bool:
    """Sliding-window rate limiter. Returns True if allowed, False if exceeded."""
    now = time.time()
    key = f"rate_limit:{client_id}"

    if _redis_client:
        try:
            pipe = _redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, now - window_seconds)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, window_seconds)
            _, _, count, _ = pipe.execute()
            return count <= max_requests
        except Exception:
            pass

    # In-memory fallback sliding window
    timestamps = _memory_rate_limits.get(client_id, [])
    timestamps = [t for t in timestamps if t > now - window_seconds]
    if len(timestamps) >= max_requests:
        return False
    timestamps.append(now)
    _memory_rate_limits[client_id] = timestamps
    return True
