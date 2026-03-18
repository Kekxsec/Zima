# backend/app/providers/base/utils.py
"""Shared utilities for provider clients."""

from __future__ import annotations

import socket
from collections.abc import Callable

# Type alias for DNS resolver functions (used by DNSBL and DNS providers).
# Signature: (hostname, record_type_tuple, timeout_seconds) -> list[str]
ResolverFunc = Callable[[str, tuple[str, ...], float], list[str]]


def default_resolver(
    hostname: str, rdtypes: tuple[str, ...], timeout: float
) -> list[str]:
    """Simple DNS A-record resolver using socket.getaddrinfo.

    Returns resolved IP addresses for the given hostname.
    Falls back to an empty list on lookup failure.
    """
    try:
        results = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM)
        return [r[4][0] for r in results]
    except (socket.gaierror, OSError):
        return []
