import logging
import os
import time
from collections import defaultdict, deque

from flask import request


security_logger = logging.getLogger("racinepoir.security")

_rate_limit_buckets = defaultdict(deque)


def security_event(event_type, **details):
    detail_text = " ".join(
        f"{key}={value}"
        for key, value in sorted(details.items())
        if value is not None
    )
    security_logger.info("%s %s", event_type, detail_text)


def request_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()


def rate_limit_key(scope, identifier=None):
    parts = [scope, request_ip()]
    if identifier:
        parts.append(str(identifier).lower())
    return ":".join(parts)


def is_rate_limited(key, limit, window_seconds):
    now = time.time()
    bucket = _rate_limit_buckets[key]

    while bucket and bucket[0] <= now - window_seconds:
        bucket.popleft()

    if len(bucket) >= limit:
        return True, max(1, int(window_seconds - (now - bucket[0])))

    bucket.append(now)
    return False, None


def env_int(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default
