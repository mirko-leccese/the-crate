import base64
from datetime import date
from io import BytesIO
import os
from pathlib import Path
import random
import re
import unicodedata
from typing import Optional
from urllib.parse import urlparse


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug (lowercase, hyphen-separated, ASCII only)."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")

import requests
from PIL import Image

class Utils:
    # Tier system — bins and labels must stay in sync with app.py _load_data()
    TIER_BINS = [0, 49, 59, 69, 74, 84, 89, 95, 100]
    TIER_LABELS = [8, 7, 6, 5, 4, 3, 2, 1]

    @staticmethod
    def tier_score_range(tier: int) -> str:
        """Returns the score interval string for a given tier number, e.g. '96–100'."""
        try:
            idx = Utils.TIER_LABELS.index(tier)
        except ValueError:
            return "?"
        lo = Utils.TIER_BINS[idx]
        hi = Utils.TIER_BINS[idx + 1]
        # First bin uses include_lowest, so all integer scores ≥ lo are included.
        # Subsequent bins are (lo, hi], so the first valid integer score is lo+1.
        lo_display = lo if idx == 0 else lo + 1
        return f"{lo_display}–{hi}"

    @staticmethod
    def map_genres(genres):
        # Normalize to a list of lowercase stripped strings for per-item matching.
        if isinstance(genres, list):
            items = [str(g).lower().strip() for g in genres if g]
        else:
            items = [str(genres).lower().strip()]

        if not items:
            return "Other"

        def has_sub(kw):
            return any(kw in g for g in items)

        def has_exact(kw):
            return kw in items

        if has_sub("r&b") or has_sub("soul"):
            return "R&B/Soul"
        if has_sub("pop rap"):
            return "Hip-Hop/Rap"
        if has_sub("pop"):
            return "Pop"
        if has_sub("punk"):
            return "Punk"
        # "Rap Metal" (exact genre name) is a metal genre — use exact match to avoid
        # catching "Trap Metal" which is a hip-hop subgenre containing "rap metal" as a substring.
        if has_exact("rap metal"):
            return "Metal"
        if has_sub("rap") or has_sub("hip-hop"):
            # Metal wins only when "Metal" is explicitly listed as its own genre alongside hip-hop.
            if has_exact("metal"):
                return "Metal"
            return "Hip-Hop/Rap"
        if has_sub("cantautorato") or has_exact("folk"):
            return "Folk"
        if has_sub("rock"):
            return "Rock"
        if has_sub("metal"):
            return "Metal"
        if has_sub("jazz"):
            return "Jazz"
        if has_sub("latin") or has_exact("reggaeton"):
            return "Latin"
        if has_sub("dance") or has_sub("electronic"):
            return "Electronic"
        if has_sub("alternative"):
            return "Alternative"
        return "Other"

    # Calcolo colore dinamico dal rosso al verde (soft)
    @staticmethod
    def get_rating_color(rating):
        # Limita il valore tra 0 e 100
        r = max(0, min(100, rating))
        # Interpolazione manuale RGB tra rosso (255,120,120) e verde (120,200,120)
        red = int(255 - (r / 100) * (255 - 120))
        green = int(120 + (r / 100) * (200 - 120))
        blue = int(120)  # fisso per tono pastello
        return f"rgb({red}, {green}, {blue})"


    # Shared Plotly theme for modern look
    @staticmethod
    def apply_plotly_theme(fig):
        fig.update_layout(
            template="plotly_white",
            paper_bgcolor="#f6f4ee",
            plot_bgcolor="#f6f4ee",
            font=dict(color="#2f2f2f", size=15, family="Inter, 'Helvetica Neue', sans-serif"),
            margin=dict(t=36, b=32, l=20, r=20),
            colorway=["#3a6ea5", "#e0a458", "#6ca36c", "#c66980", "#7d8ca3"]
        )

        shared_axis_style = dict(
            showgrid=False,
            zeroline=False,
            color="#6b7280",
            title_font=dict(size=16, color="#1f2933"),
            tickfont=dict(size=12, color="#4b5563")
        )

        fig.update_xaxes(**shared_axis_style)
        fig.update_yaxes(**shared_axis_style)

        return fig 

    @staticmethod
    def rating_bin(x):
        if x == 100:
            return "100 (Masterpiece)"
        elif x > 95 and x < 100:
            return "95-99 (Excellent)"
        elif x >= 90 and x <= 95:
            return "90-94 (Great)"
        elif x >= 80 and x < 89:
            return "80-89 (Good)"
        elif x >= 70 and x < 80:
            return "70-79 (Decent)"
        elif x >= 60 and x < 69:
            return "60-69 (Mediocre)"
        elif x >= 50 and x < 59:
            return "50-59 (Poor)"
        elif x < 50:
            return "<50 (Bad)"

    @staticmethod 
    def rating_bin_order(x):
        if x == 100:
            return 1
        elif x > 95 and x < 100:
            return 2
        elif x >= 90 and x <= 95:
            return 3
        elif x >= 80 and x < 89:
            return 4
        elif x >= 70 and x < 80:
            return 5
        elif x >= 60 and x < 69:
            return 6
        elif x >= 50 and x < 59:
            return 7
        elif x < 50:
            return 8

    @staticmethod
    def is_url(path: str) -> bool:
        parsed = urlparse(str(path))
        return parsed.scheme in ("http", "https")

    @staticmethod
    def read_image_as_data_uri(path: Path) -> Optional[str]:
        target = Path(path)
        if not target.exists():
            return None
        try:
            content = target.read_bytes()
        except OSError:
            return None
        if not content:
            return None
        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        mime_type = mime_map.get(target.suffix.lower(), "image/png")
        b64 = base64.b64encode(content).decode("ascii")
        return f"data:{mime_type};base64,{b64}"


def get_album_of_the_day(df) -> Optional[dict]:
    """Return a single album dict deterministically chosen for today.

    Selection criteria:
    - Score >= 75
    - cover_url must be non-empty (so there is always a cover to display)

    The seed is derived from today's date (YYYYMMDD) so the same album is
    returned for the entire day across all server workers and page loads,
    and automatically rotates at midnight.

    df.sample() uses numpy's RNG internally and ignores random.seed(), so
    we use random.choice() on a plain Python list of positional indices instead.
    """
    import pandas as pd
    from libs.streaming_links import spotify_search_url, apple_music_search_url

    if df is None or df.empty:
        return None

    pool = df[
        (df["Score"] >= 75) &
        (df["cover_url"].notna()) &
        (df["cover_url"].str.strip() != "")
    ]

    if pool.empty:
        return None

    seed = int(date.today().strftime("%Y%m%d"))
    random.seed(seed)
    chosen_idx = random.choice(list(range(len(pool))))
    row = pool.iloc[chosen_idx]

    def _s(v):
        if v is None:
            return ""
        try:
            if pd.isna(v):
                return ""
        except (TypeError, ValueError):
            pass
        return str(v)

    def _fmt_score(v):
        try:
            f = float(v)
            return "-" if pd.isna(f) else f"{f:.1f}"
        except (TypeError, ValueError):
            return "-"

    def _fmt_dur(v):
        try:
            mins = int(float(v))
            if mins < 60:
                return f"{mins} min"
            h, m = divmod(mins, 60)
            return f"{h}h {m} min"
        except (TypeError, ValueError):
            return "/"

    genres = row.get("Genre", [])
    if not isinstance(genres, list):
        genres = []

    score_raw = row.get("Score")
    try:
        score = float(score_raw) if pd.notna(score_raw) else None
    except (TypeError, ValueError):
        score = None

    tier_raw = row.get("Tier")
    try:
        tier = int(tier_raw) if pd.notna(tier_raw) else None
    except (TypeError, ValueError):
        tier = None

    rank_raw = row.get("Rank")
    try:
        rank = int(rank_raw) if pd.notna(rank_raw) else None
    except (TypeError, ValueError):
        rank = None

    release_year_raw = row.get("Release Year")
    try:
        release_year = int(release_year_raw) if pd.notna(release_year_raw) else None
    except (TypeError, ValueError):
        release_year = None

    release_date = row.get("Release Date")
    release_date_str = ""
    if release_date is not None and not (isinstance(release_date, float) and pd.isna(release_date)):
        try:
            if hasattr(release_date, "strftime"):
                release_date_str = release_date.strftime("%-d %b %Y")
        except (ValueError, AttributeError):
            pass

    created_raw = row.get("Created")
    created_formatted = ""
    if created_raw is not None and not (isinstance(created_raw, float) and pd.isna(created_raw)):
        try:
            if hasattr(created_raw, "strftime"):
                created_formatted = created_raw.strftime("%-d %b %Y")
        except (ValueError, AttributeError):
            pass

    artist = _s(row.get("Artist"))
    name = _s(row.get("Name"))
    cover_url = _s(row.get("cover_url"))

    return {
        # Keys matching album_card.html partial expectations
        "name": name,
        "artist": artist,
        "release_year": release_year,
        "release_date_str": release_date_str,
        "score": score,
        "score_display": _fmt_score(score_raw),
        "tier": tier,
        "rank": rank,
        "genres": genres,
        "unique_genre": _s(row.get("unique_genre")),
        "notes": _s(row.get("Notes")),
        "best_track": _s(row.get("Best Track")),
        "cover_url": cover_url,
        "overall": _fmt_score(row.get("Overall")),
        "production": _fmt_score(row.get("Production")),
        "lyrics_novelty": _fmt_score(row.get("Lyrics/Novelty")),
        "masterpiece_tracks": row.get("Masterpiece Tracks"),
        "masterpiece_track_titles": _s(row.get("Masterpiece Track Titles")),
        "total_tracks": int(row["Total Tracks"]) if pd.notna(row.get("Total Tracks")) else None,
        "duration": _fmt_dur(row.get("Duration")),
        "special": bool(row.get("Special", False)),
        "language": _s(row.get("Language")),
        "color": _s(row.get("Color")),
        "slug": _s(row.get("slug")),
        "spotify_url": spotify_search_url(artist, name),
        "apple_music_url": apple_music_search_url(artist, name),
        "created_formatted": created_formatted,
        # Minimum required keys specified in task description
        "album_name": name,
        "cover_image": cover_url,
        "genre": genres,
        "note": _s(row.get("Notes")),
    }
