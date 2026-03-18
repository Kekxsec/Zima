# backend/app/core/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared limiter instance — import from here in all endpoint modules.
# This avoids circular imports: main.py → router → endpoint → main.py.
limiter = Limiter(key_func=get_remote_address)
