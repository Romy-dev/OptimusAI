"""URL scraper service — fetch and extract text content from web pages."""

import re
from urllib.parse import urlparse

import httpx
import structlog

logger = structlog.get_logger()

MAX_CONTENT_LENGTH = 50_000
USER_AGENT = (
    "Mozilla/5.0 (compatible; OptimusAI/1.0; +https://optimusai.africa)"
)
REQUEST_TIMEOUT = 15.0


def _is_youtube_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.hostname in (
        "www.youtube.com",
        "youtube.com",
        "youtu.be",
        "m.youtube.com",
    )


def _is_social_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return any(
        domain in host
        for domain in ("facebook.com", "instagram.com", "fb.com", "fb.watch")
    )


def _extract_meta(html: str, name: str) -> str:
    """Extract content from a <meta> tag by name or property."""
    patterns = [
        rf'<meta\s+(?:name|property)="{name}"\s+content="([^"]*)"',
        rf'<meta\s+content="([^"]*)"\s+(?:name|property)="{name}"',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def _extract_title(html: str) -> str:
    """Extract <title> tag content."""
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""


def _strip_tags(html: str) -> str:
    """Remove HTML tags and decode common entities."""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode common HTML entities
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    text = text.replace("&nbsp;", " ")
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_structured_content(html: str) -> str:
    """Extract content from semantic HTML elements (h1-h6, p, li)."""
    parts: list[str] = []

    # Headings
    for tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
        for match in re.finditer(
            rf"<{tag}[^>]*>(.*?)</{tag}>", html, re.IGNORECASE | re.DOTALL
        ):
            text = _strip_tags(match.group(1)).strip()
            if text:
                parts.append(f"\n\n## {text}\n")

    # Paragraphs
    for match in re.finditer(
        r"<p[^>]*>(.*?)</p>", html, re.IGNORECASE | re.DOTALL
    ):
        text = _strip_tags(match.group(1)).strip()
        if text and len(text) > 10:
            parts.append(text)

    # List items
    for match in re.finditer(
        r"<li[^>]*>(.*?)</li>", html, re.IGNORECASE | re.DOTALL
    ):
        text = _strip_tags(match.group(1)).strip()
        if text:
            parts.append(f"- {text}")

    return "\n\n".join(parts)


def _extract_youtube_content(html: str) -> str:
    """Extract YouTube video metadata from page HTML."""
    title = _extract_meta(html, "og:title") or _extract_title(html)
    description = (
        _extract_meta(html, "og:description")
        or _extract_meta(html, "description")
    )
    channel = _extract_meta(html, "og:site_name") or "YouTube"

    parts = []
    if title:
        parts.append(f"Titre: {title}")
    if channel and channel != "YouTube":
        parts.append(f"Chaine: {channel}")
    if description:
        parts.append(f"Description: {description}")

    return "\n\n".join(parts) if parts else ""


def _extract_social_content(html: str) -> str:
    """Extract social media post content from OG tags and visible text."""
    title = _extract_meta(html, "og:title") or _extract_title(html)
    description = (
        _extract_meta(html, "og:description")
        or _extract_meta(html, "description")
    )

    parts = []
    if title:
        parts.append(title)
    if description:
        parts.append(description)

    # Try to get structured content as fallback
    if not parts:
        structured = _extract_structured_content(html)
        if structured:
            parts.append(structured)

    return "\n\n".join(parts)


async def scrape_url(url: str) -> dict:
    """Scrape a URL and return structured content.

    Returns:
        {"title": "...", "description": "...", "content": "...", "url": url}

    Raises:
        ValueError: If the URL cannot be fetched or has no extractable content.
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.hostname:
        raise ValueError(f"Invalid URL: {url}")

    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise ValueError(f"HTTP error {e.response.status_code} fetching {url}") from e
    except httpx.RequestError as e:
        raise ValueError(f"Failed to fetch URL {url}: {e}") from e

    html = response.text
    if not html:
        raise ValueError("Empty response from URL")

    # Extract title and description from meta tags
    title = _extract_meta(html, "og:title") or _extract_title(html)
    description = (
        _extract_meta(html, "og:description")
        or _extract_meta(html, "description")
    )

    # Extract content based on URL type
    if _is_youtube_url(url):
        content = _extract_youtube_content(html)
    elif _is_social_url(url):
        content = _extract_social_content(html)
    else:
        # General web page: prefer structured extraction, fall back to full strip
        content = _extract_structured_content(html)
        if not content or len(content) < 50:
            content = _strip_tags(html)

    # Truncate to max length
    if len(content) > MAX_CONTENT_LENGTH:
        content = content[:MAX_CONTENT_LENGTH] + "\n\n[Contenu tronque a 50 000 caracteres]"

    if not content or len(content.strip()) < 10:
        raise ValueError("No meaningful content could be extracted from the URL")

    logger.info(
        "url_scraped",
        url=url,
        title=title[:100] if title else "",
        content_length=len(content),
    )

    return {
        "title": title,
        "description": description,
        "content": content,
        "url": url,
    }
