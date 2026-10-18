"""Web retrieval service with SSRF protection."""

from __future__ import annotations

import hashlib
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings
from app.models.schemas import Source, _hash
from app.services.security import (
    MAX_RESPONSE_SIZE,
    sanitize_html,
    strip_prompt_injection,
    validate_url,
)


async def fetch_url(url: str, timeout: int | None = None) -> Optional[dict]:
    """Fetch and extract text content from a URL.

    Returns: {"url": str, "title": str, "content": str, "content_hash": str}
    or None on failure.
    """
    is_valid, reason = validate_url(url)
    if not is_valid:
        return None

    timeout = timeout or settings.request_timeout
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            max_redirects=3,
        ) as client:
            response = await client.get(
                url,
                headers={"User-Agent": "DeepDive-Research/1.0"},
            )
            response.raise_for_status()

            # Size check
            content_length = len(response.content)
            if content_length > MAX_RESPONSE_SIZE:
                return None

            # Content-type check
            ct = response.headers.get("content-type", "")
            if "text/html" not in ct and "text/plain" not in ct and "application/json" not in ct:
                return None

            text = response.text
            title = ""

            if "text/html" in ct:
                soup = BeautifulSoup(text, "html.parser")
                # Remove script/style
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()
                title = soup.title.string if soup.title else ""
                text = soup.get_text(separator="\n", strip=True)

            # Truncate very long content
            if len(text) > 50000:
                text = text[:50000]

            # Clean prompt injection
            text = strip_prompt_injection(text)

            return {
                "url": str(response.url),
                "title": title or url,
                "content": text,
                "content_hash": _hash(text),
            }

    except (httpx.HTTPError, Exception):
        return None


async def search_web(query: str) -> list[str]:
    """Simple web search returning URLs.

    Uses a search API if available, otherwise returns empty.
    In production, integrate with a search API.
    For hackathon demo, this returns placeholder results that
    the orchestrator can supplement with user-provided URLs.
    """
    # This is a stub — in production, wire to a search API
    # For the hackathon, users can provide source URLs directly
    return []


async def fetch_sources(urls: list[str]) -> list[Source]:
    """Fetch multiple URLs and return Source objects."""
    sources = []
    seen_hashes: set[str] = set()

    for url in urls:
        result = await fetch_url(url)
        if result is None:
            continue

        # Duplicate detection
        if result["content_hash"] in seen_hashes:
            continue
        seen_hashes.add(result["content_hash"])

        source = Source(
            url=result["url"],
            title=result["title"],
            content_hash=result["content_hash"],
            content_snippet=result["content"][:500],
        )
        sources.append(source)

    return sources
