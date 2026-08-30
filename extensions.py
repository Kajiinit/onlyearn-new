import os

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


redis_url = os.environ.get("REDIS_URL")

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri=redis_url or "memory://",
)