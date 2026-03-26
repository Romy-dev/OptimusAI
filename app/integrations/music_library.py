"""Music library — free royalty-free background music for stories and videos.

Sources:
- Pixabay Music (CC0, no attribution required)
- Local library of pre-downloaded tracks by mood

Each mood has multiple tracks to avoid repetition.
"""

import asyncio
import os
import random
from pathlib import Path

import httpx
import structlog

logger = structlog.get_logger()

MUSIC_DIR = Path("/tmp/optimusai_music")

# Pixabay API for music search
PIXABAY_API_KEY = "47338169-c9c89b3b7fffe4f53faf5aeab"  # Free tier key

# Mood to search query mapping
MOOD_QUERIES = {
    "upbeat": "upbeat happy energetic pop",
    "chill": "chill lofi relaxing calm",
    "dramatic": "dramatic cinematic epic",
    "inspiring": "inspiring motivational corporate",
    "festive": "celebration party afrobeat",
    "elegant": "elegant luxury piano jazz",
    "warm": "warm acoustic guitar folk",
    "urgent": "urgent countdown tense",
    "playful": "playful fun quirky",
    "african": "afrobeat african drums tropical",
}


async def get_music_for_mood(mood: str, duration_s: float = 15.0) -> str | None:
    """Get a music file path for the given mood.

    First checks local cache, then downloads from Pixabay.
    Returns path to MP3 file, or None if unavailable.
    """
    mood = mood.lower().strip()
    if mood not in MOOD_QUERIES:
        mood = "upbeat"

    # Check local cache
    mood_dir = MUSIC_DIR / mood
    if mood_dir.exists():
        tracks = list(mood_dir.glob("*.mp3"))
        if tracks:
            chosen = random.choice(tracks)
            logger.info("music_from_cache", mood=mood, file=chosen.name)
            return str(chosen)

    # Download from Pixabay
    try:
        return await _download_from_pixabay(mood, duration_s)
    except Exception as e:
        logger.warning("music_download_failed", mood=mood, error=str(e)[:100])
        return None


async def _download_from_pixabay(mood: str, duration_s: float) -> str | None:
    """Download a music track from Pixabay Music API."""
    query = MOOD_QUERIES.get(mood, "background music")

    # Pixabay doesn't have a public music API like their image API
    # We'll use their audio search endpoint
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            "https://pixabay.com/api/",
            params={
                "key": PIXABAY_API_KEY,
                "q": query,
                "media_type": "music",
                "per_page": 5,
                "min_duration": max(10, int(duration_s) - 5),
                "max_duration": int(duration_s) + 30,
            },
        )

        if resp.status_code != 200:
            logger.warning("pixabay_api_error", status=resp.status_code)
            return None

        data = resp.json()
        hits = data.get("hits", [])
        if not hits:
            return None

        # Pick a random track
        track = random.choice(hits)
        audio_url = track.get("audio", track.get("previewURL"))

        if not audio_url:
            return None

        # Download
        audio_resp = await client.get(audio_url)
        if audio_resp.status_code != 200:
            return None

        # Save to cache
        mood_dir = MUSIC_DIR / mood
        mood_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{track.get('id', uuid.uuid4().hex)}.mp3"
        filepath = mood_dir / filename

        with open(filepath, "wb") as f:
            f.write(audio_resp.content)

        logger.info("music_downloaded", mood=mood, file=filename, size_kb=len(audio_resp.content) // 1024)
        return str(filepath)


async def ensure_default_library():
    """Pre-download a basic set of music tracks for each mood.

    Called once at startup or manually to populate the cache.
    """
    for mood in MOOD_QUERIES:
        existing = list((MUSIC_DIR / mood).glob("*.mp3")) if (MUSIC_DIR / mood).exists() else []
        if len(existing) >= 2:
            continue

        try:
            path = await _download_from_pixabay(mood, 15.0)
            if path:
                logger.info("default_music_cached", mood=mood)
        except Exception as e:
            logger.warning("default_music_failed", mood=mood, error=str(e)[:60])

        await asyncio.sleep(1)  # Rate limit
