"""
libs/deezer.py — Deezer API helper for 30-second track preview URLs.

No authentication required. Results are cached in-memory for the lifetime
of the Flask process so that each unique (artist, track) pair hits the
Deezer API at most once. Subsequent page loads return instantly from cache.
"""

import requests

# Module-level in-memory cache: (artist_lower, track_lower) -> url | None
_cache: dict = {}


def get_preview_url(artist: str, best_track: str) -> str | None:
    """Return a 30-second Deezer MP3 preview URL for the given artist/track.

    Returns None if the track is not found or if any error occurs so that
    callers never need to handle exceptions from this function.
    """
    key = (artist.strip().lower(), best_track.strip().lower())
    if key in _cache:
        return _cache[key]

    url = None
    try:
        q = f'artist:"{artist}" track:"{best_track}"'
        resp = requests.get(
            "https://api.deezer.com/search",
            params={"q": q, "limit": 1},
            timeout=2,
        )
        data = resp.json().get("data", [])
        if data:
            url = data[0].get("preview") or None
    except Exception:
        # Network error, timeout, or malformed response — degrade silently
        pass

    _cache[key] = url
    return url
