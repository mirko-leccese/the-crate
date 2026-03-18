"""
libs/streaming_links.py — Build streaming platform search URLs.

Pure string operations — no API calls, no caching needed.
"""

from urllib.parse import quote_plus, quote


def spotify_search_url(artist: str, album: str) -> str:
    query = quote_plus(f"{artist} {album}")
    return f"https://open.spotify.com/search/{query}"


def apple_music_search_url(artist: str, album: str) -> str:
    # Use quote() not quote_plus() — Apple Music's ?term= parameter breaks on literal
    # '+' characters that quote_plus() produces; %20 (from quote) works correctly.
    # .title() normalises ALL-CAPS album names from the database before encoding.
    # No locale prefix — Apple Music redirects to the correct regional storefront.
    query = f"{artist} {album}".title()
    return f"https://music.apple.com/search?term={quote(query, safe='')}"
