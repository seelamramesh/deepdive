"""Security utilities: SSRF protection, URL validation, sanitization."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

import bleach

# Private/reserved IP ranges to block
_BLOCKED_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

_BLOCKED_HOSTS = {"localhost", "metadata.google.internal", "169.254.169.254"}

MAX_RESPONSE_SIZE = 5 * 1024 * 1024  # 5MB


def validate_url(url: str) -> tuple[bool, str]:
    """Validate URL for SSRF protection. Returns (is_valid, reason)."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format"

    if parsed.scheme not in ("http", "https"):
        return False, f"Blocked scheme: {parsed.scheme}"

    hostname = parsed.hostname or ""
    if not hostname:
        return False, "No hostname"

    if hostname.lower() in _BLOCKED_HOSTS:
        return False, f"Blocked host: {hostname}"

    # Check if hostname is an IP address in a blocked range
    try:
        addr = ipaddress.ip_address(hostname)
        for network in _BLOCKED_RANGES:
            if addr in network:
                return False, f"Blocked private IP: {hostname}"
    except ValueError:
        pass  # Not an IP address, hostname is fine

    return True, "ok"


def sanitize_html(html: str) -> str:
    """Sanitize HTML content to prevent XSS."""
    return bleach.clean(
        html,
        tags=["p", "br", "b", "i", "em", "strong", "a", "ul", "ol", "li",
              "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "code", "pre"],
        attributes={"a": ["href", "title"]},
        strip=True,
    )


def strip_prompt_injection(text: str) -> str:
    """Remove common prompt injection patterns from retrieved content."""
    # Remove patterns that look like system/instruction prompts
    patterns = [
        r"(?i)\[?(system|instruction|ignore previous|disregard|forget)\]?[:\s]",
        r"(?i)you are now\s",
        r"(?i)new instructions?:\s",
        r"(?i)override\s+(all\s+)?(previous\s+)?instructions?",
    ]
    cleaned = text
    for pattern in patterns:
        cleaned = re.sub(pattern, "[FILTERED] ", cleaned)
    return cleaned
