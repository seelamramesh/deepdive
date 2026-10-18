"""Security utilities: SSRF protection, URL validation, sanitization."""

from __future__ import annotations

import ipaddress
import html
import re
import socket
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


def render_report_markdown(markdown_text: str) -> str:
    """Render the small report Markdown subset without allowing raw HTML."""
    rendered: list[str] = []
    paragraph: list[str] = []
    in_list = False

    def inline(value: str) -> str:
        safe = html.escape(value)
        safe = re.sub(
            r"\[evidence:(\w+)\]",
            r'<a class="citation" href="#evidence-\1">evidence:\1</a>',
            safe,
        )
        safe = re.sub(
            r"\[claim:(\w+)\]",
            r'<span class="claim-marker" title="Verified claim">✓</span>',
            safe,
        )
        safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)
        safe = re.sub(r"`([^`]+)`", r"<code>\1</code>", safe)
        return safe

    def flush_paragraph() -> None:
        if paragraph:
            rendered.append(f"<p>{inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if not line:
            flush_paragraph()
            if in_list:
                rendered.append("</ul>")
                in_list = False
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            if in_list:
                rendered.append("</ul>")
                in_list = False
            level = len(heading.group(1))
            rendered.append(f"<h{level}>{inline(heading.group(2))}</h{level}>")
            continue
        if line.startswith("- "):
            flush_paragraph()
            if not in_list:
                rendered.append("<ul>")
                in_list = True
            rendered.append(f"<li>{inline(line[2:])}</li>")
            continue
        paragraph.append(line)

    flush_paragraph()
    if in_list:
        rendered.append("</ul>")
    return "\n".join(rendered)


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

    # Check literal and DNS-resolved addresses.
    try:
        addresses = {ipaddress.ip_address(hostname)}
    except ValueError:
        try:
            addresses = {
                ipaddress.ip_address(item[4][0])
                for item in socket.getaddrinfo(hostname, parsed.port or 443)
            }
        except (socket.gaierror, ValueError):
            return False, f"Hostname could not be resolved: {hostname}"

    for addr in addresses:
        if any(addr in network for network in _BLOCKED_RANGES):
            return False, f"Blocked private IP: {addr}"

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
