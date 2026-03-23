import base64
from io import BytesIO
import os
from pathlib import Path
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
    def map_genres(genre: str):
        lower_genre = str(genre).lower()
        if "r&b" in lower_genre or "soul" in lower_genre:
            return "R&B/Soul"
        elif "pop rap" in lower_genre:
            return "Hip-Hop/Rap"
        elif "pop" in lower_genre:
            return "Pop"
        elif "punk" in lower_genre:
            return "Punk"
        elif "rap metal" in lower_genre:
            return "Metal"
        elif "rap" in lower_genre or "hip-hop" in lower_genre:
            return "Hip-Hop/Rap"
        elif "cantautorato" in lower_genre or lower_genre == "folk":
            return "Folk"
        elif "rock" in lower_genre: 
            return "Rock"
        elif "metal" in lower_genre:
            return "Metal"
        elif "jazz" in lower_genre:
            return "Jazz"
        elif "latin" in lower_genre or lower_genre == "reggaeton":
            return "Latin"
        elif "dance" in lower_genre or "electronic" in lower_genre:
            return "Electronic"
        elif "alternative" in lower_genre:
            return "Alternative"
        else:
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
