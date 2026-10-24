"""Web retrieval service with SSRF protection."""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Optional
from urllib.parse import urljoin

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
            follow_redirects=False,
        ) as client:
            current_url = url
            for _ in range(4):
                is_valid, _ = validate_url(current_url)
                if not is_valid:
                    return None
                response = await client.get(
                    current_url,
                    headers={"User-Agent": "DeepDive-Research/1.0"},
                )
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        return None
                    current_url = urljoin(str(response.url), location)
                    continue
                break
            else:
                return None
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
    """Search Brave for public source URLs when configured."""
    if not settings.brave_search_api_key:
        return []
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": settings.max_sources_per_round},
                headers={"Accept": "application/json", "X-Subscription-Token": settings.brave_search_api_key},
            )
            response.raise_for_status()
            results = response.json().get("web", {}).get("results", [])
            urls = []
            for item in results:
                candidate = item.get("url", "")
                valid, _ = validate_url(candidate)
                if valid and candidate not in urls:
                    urls.append(candidate)
            return urls[: settings.max_sources_per_round]
    except (httpx.HTTPError, ValueError, TypeError):
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
            content_snapshot=result["content"],
        )
        sources.append(source)

    return sources


def select_extraction_window(snapshot: str, question: str, limit: int = 7000) -> tuple[str, int, int]:
    """Choose one bounded, contiguous source slice using lexical query coverage.

    This is a retrieval heuristic, not evidence verification. Ties retain the
    earliest window; no matching terms retain the historical first slice.
    """
    if limit <= 0:
        raise ValueError("Extraction limit must be positive")
    if len(snapshot) <= limit:
        return snapshot, 0, len(snapshot)
    stopwords = {"what", "which", "when", "where", "with", "from", "that", "this",
                 "have", "does", "about", "will", "could", "would", "should", "into"}
    terms = set(re.findall(r"[^\W_]{3,}", question.casefold())) - stopwords
    matches = [(match.start(), match.group().casefold())
               for match in re.finditer(r"[^\W_]{3,}", snapshot)
               if match.group().casefold() in terms]
    starts = set(range(0, len(snapshot) - limit + 1, max(1, limit // 2)))
    starts.add(len(snapshot) - limit)
    def score(start):
        counts = Counter(term for position, term in matches if start <= position < start + limit)
        return len(counts), sum(min(count, 3) for count in counts.values()), -start
    start = max(starts, key=score)
    end = min(start + limit, len(snapshot))
    return snapshot[start:end], start, end
