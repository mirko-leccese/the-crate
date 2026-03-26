import json
import logging
import os
import random as _random
from datetime import datetime
from pathlib import Path

import pandas as pd
from flask import Flask, render_template, request, jsonify

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import sqlite3

from libs.utils import Utils, slugify
from libs.streaming_links import spotify_search_url, apple_music_search_url
from libs.stats import (
    get_latest_release_year,
    get_summary_stats,
    get_tier_distribution,
    get_albums_per_year,
    get_genre_breakdown,
    get_artist_spotlight,
    get_subgenre_scatter,
    get_genre_cards,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.context_processor
def inject_analytics():
    return dict(umami_id=os.environ.get("UMAMI_WEBSITE_ID", ""))

# ---------------------------------------------------------------------------
# Data layer — loaded once at startup
# ---------------------------------------------------------------------------

DB_PATH = "albums.db"
CONF_PATH = Path("conf.json")

_album_df: pd.DataFrame = pd.DataFrame()
_load_error: str = ""

# Load other_scores config once at startup
_other_scores: list = []
if CONF_PATH.exists():
    with open(CONF_PATH) as _f:
        _other_scores = json.load(_f).get("other_scores", [])


def _load_data() -> None:
    global _album_df, _load_error

    try:
        db_path = Path(DB_PATH)
        if not db_path.exists():
            raise FileNotFoundError(
                f"Database file '{DB_PATH}' not found. "
                "Run 'python notion_to_sqlite.py' first to migrate data from Notion."
            )

        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT * FROM albums", conn)
        conn.close()

        # Genre was serialized as a JSON string in SQLite — restore to list
        df["Genre"] = df["Genre"].apply(
            lambda x: json.loads(x) if isinstance(x, str) else []
        )

        # Keep only published albums
        df = df[df["Published"] == True].reset_index(drop=True)

        # Derived columns
        df["unique_genre"] = df["Genre"].apply(Utils.map_genres)

        df = df.sort_values(
            by=["Score", "Lyrics/Novelty", "Production", "Masterpiece Tracks", "Name"],
            ascending=[False, False, False, False, True],
        ).reset_index(drop=True)

        df["Rank"] = df.index + 1

        tier_bins = Utils.TIER_BINS
        tier_labels = Utils.TIER_LABELS
        df["Tier"] = pd.cut(
            df["Score"], bins=tier_bins, labels=tier_labels,
            right=True, include_lowest=True,
        ).astype(int)

        # Cover URL: prefer local artwork, fall back to external URL
        def _cover_url(row):
            picname = row.get("Picname")
            if picname and pd.notna(picname) and str(picname).strip():
                return f"/static/artworks/{str(picname).strip()}"
            cover = row.get("Cover")
            if cover and pd.notna(cover) and str(cover).strip():
                return str(cover).strip()
            return ""

        df["cover_url"] = df.apply(_cover_url, axis=1)

        # Slug for clean URLs: artist + album title → e.g. "kendrick-lamar-good-kid-maad-city"
        df["slug"] = df.apply(
            lambda r: slugify(str(r.get("Artist", "")) + " " + str(r.get("Name", ""))),
            axis=1,
        )

        # Parse dates
        df["Created"] = pd.to_datetime(df["Created"], utc=True, errors="coerce")
        if "Release Date" not in df.columns:
            df["Release Date"] = pd.NaT
        df["Release Date"] = pd.to_datetime(df["Release Date"], errors="coerce")

        # Ensure Release Year is int-compatible
        df["Release Year"] = pd.to_numeric(df["Release Year"], errors="coerce")

        _album_df = df
        logger.info("Loaded %d albums from SQLite.", len(df))

    except Exception as exc:
        _load_error = str(exc)
        logger.error("Failed to load album data: %s", exc)
        _album_df = pd.DataFrame()


def get_data() -> pd.DataFrame:
    return _album_df


# Load at import time (works with gunicorn workers)
_load_data()


# ---------------------------------------------------------------------------
# Genre descriptions — shown below the title on each genre page
# ---------------------------------------------------------------------------

GENRE_DESCRIPTIONS: dict[str, str] = {
    "Rock": (
        "Chitarre distorte, ritornelli che non escono più dalla testa, leggende e meteore. "
        "Dal garage al Madison Square Garden, il rock è ancora vivo — anche se qualcuno "
        "continua a dirci il contrario."
    ),
    "Metal": (
        "Riff pesanti come macigni, blast beat e growl che svegliano i vicini. "
        "Dai classici immortali al black metal più estremo: benvenuto nel lato oscuro."
    ),
    "Punk": (
        "Tre accordi, due minuti e tanta rabbia. Il punk non è morto — si è solo un po' "
        "ripulito. O forse no."
    ),
    "Jazz": (
        "Improvvisazione, swing, blue note e silenzi che parlano. Il jazz è il genere che "
        "più ti chiede di stare a sentire davvero. Vale la pena farlo."
    ),
    "Pop": (
        "Il genere che tutti ascoltano e pochi ammettono. Qui non ci sono sensi di colpa: "
        "un bel ritornello è un bel ritornello, punto."
    ),
    "Folk": (
        "Storie vere, voci ruvide, strumenti acustici e radici profonde. Il folk è la "
        "musica di chi aveva qualcosa da dire e non aveva bisogno di effetti speciali per dirlo."
    ),
    "Latin": (
        "Ritmo nel sangue, melodie che non si dimenticano, reggaeton e una Corona vista mare. "
        "Bienvenidos."
    ),
    "Electronic": (
        "Sintetizzatori, campionatori, BPM a volontà. La musica fatta di circuiti e visioni "
        "— dal club alle cuffie alle tre di notte."
    ),
    "Hip-Hop/Rap": (
        "Rime taglienti, flow alieni e bassi che sfondano le casse della macchina. "
        "Dagli States all'Italia, il meglio - e il peggio - del genere più popolare del momento!"
    ),
    "R&B/Soul": (
        "Voce, groove e sentimento — il resto è contorno. Dall'era Motown alle produzioni "
        "ultra-moderne, l'anima della musica nera non smette mai di sorprendere."
    ),
}

# ---------------------------------------------------------------------------
# Template filters
# ---------------------------------------------------------------------------

@app.template_filter('score_color')
def score_color_filter(score):
    try:
        s = float(score)
        if s >= 90:
            return '#e8a020'
        elif s >= 75:
            return '#4a90d9'
        elif s >= 60:
            return '#3a9e6a'
    except (TypeError, ValueError):
        pass
    return '#cccccc'


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------

def _safe_str(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value)


def _fmt_score(value) -> str:
    try:
        f = float(value)
        if pd.isna(f):
            return "-"
        return f"{f:.1f}"
    except (TypeError, ValueError):
        return "-"


def _fmt_duration(value) -> str:
    try:
        mins = int(float(value))
        if mins < 60:
            return f"{mins} min"
        h, m = divmod(mins, 60)
        return f"{h}h {m} min"
    except (TypeError, ValueError):
        return "/"


def _row_to_dict(row: pd.Series) -> dict:
    """Convert a DataFrame row to a clean dict for template rendering."""
    genres = row.get("Genre", [])
    if not isinstance(genres, list):
        genres = []

    score_raw = row.get("Score")
    score_display = _fmt_score(score_raw)
    try:
        score_numeric = float(score_raw) if pd.notna(score_raw) else None
    except (TypeError, ValueError):
        score_numeric = None

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

    return {
        "name": _safe_str(row.get("Name")),
        "artist": _safe_str(row.get("Artist")),
        "release_year": release_year,
        "release_date_str": release_date_str,
        "score": score_numeric,
        "score_display": score_display,
        "tier": tier,
        "rank": rank,
        "genres": genres,
        "unique_genre": _safe_str(row.get("unique_genre")),
        "notes": _safe_str(row.get("Notes")),
        "best_track": _safe_str(row.get("Best Track")),
        "cover_url": _safe_str(row.get("cover_url")),
        "overall": _fmt_score(row.get("Overall")),
        "production": _fmt_score(row.get("Production")),
        "lyrics_novelty": _fmt_score(row.get("Lyrics/Novelty")),
        "masterpiece_tracks": row.get("Masterpiece Tracks"),
        "masterpiece_track_titles": _safe_str(row.get("Masterpiece Track Titles")),
        "total_tracks": int(row["Total Tracks"]) if pd.notna(row.get("Total Tracks")) else None,
        "duration": _fmt_duration(row.get("Duration")),
        "special": bool(row.get("Special", False)),
        "language": _safe_str(row.get("Language")),
        "color": _safe_str(row.get("Color")),
        "slug": _safe_str(row.get("slug")),
        # Streaming search URLs: pure string ops, no API call needed.
        "spotify_url": spotify_search_url(
            _safe_str(row.get("Artist")), _safe_str(row.get("Name"))
        ),
        "apple_music_url": apple_music_search_url(
            _safe_str(row.get("Artist")), _safe_str(row.get("Name"))
        ),
        "created_formatted": created_formatted,
    }


# ---------------------------------------------------------------------------
# Filter helpers (shared by /top and /genere routes)
# ---------------------------------------------------------------------------

def _build_filter_options(df: pd.DataFrame) -> dict:
    """Derive all filter option lists from a DataFrame slice."""
    all_subgenres = sorted(set(
        g for genres_list in df["Genre"].dropna()
        if isinstance(genres_list, list)
        for g in genres_list
        if g
    ))
    all_years = sorted([int(y) for y in df["Release Year"].dropna().unique()], reverse=True)
    all_languages = sorted([x for x in df["Language"].dropna().unique() if str(x).strip()])
    all_colors = sorted([x for x in df["Color"].dropna().unique() if str(x).strip()])
    global_score_min = int(df["Score"].min()) if not df["Score"].dropna().empty else 0
    global_score_max = int(df["Score"].max()) if not df["Score"].dropna().empty else 100
    dataset_year_max = int(df["Release Year"].dropna().max()) if not df["Release Year"].dropna().empty else None
    return dict(
        all_subgenres=all_subgenres,
        all_years=all_years,
        all_languages=all_languages,
        all_colors=all_colors,
        global_score_min=global_score_min,
        global_score_max=global_score_max,
        dataset_year_max=dataset_year_max,
    )


def _read_filter_params(opts: dict, default_year_to_max: bool = False) -> dict:
    """Read filter parameters from request.args.

    When default_year_to_max is True, year_min/year_max default to
    dataset_year_max when omitted.  When False, year bounds default to
    None so no year filter is applied (show all years by default).
    """
    global_score_min = opts["global_score_min"]
    dataset_year_max = opts["dataset_year_max"]

    selected_subgenres = request.args.getlist("subgenre")
    # Multi-select language filter; param name is "lingua"
    selected_languages = request.args.getlist("lingua")
    selected_color = request.args.get("color", "")
    sort = request.args.get("sort", "created")

    year_fallback = dataset_year_max if default_year_to_max else None
    try:
        # Support both year_min and anno_min (used by archivio Esplora links)
        year_min = int(request.args.get("year_min", "") or request.args.get("anno_min", ""))
    except (ValueError, TypeError):
        year_min = year_fallback
    try:
        # Support both year_max and anno_max (used by archivio Esplora links)
        year_max = int(request.args.get("year_max", "") or request.args.get("anno_max", ""))
    except (ValueError, TypeError):
        year_max = year_fallback
    try:
        score_min = int(request.args.get("score_min", global_score_min))
    except (ValueError, TypeError):
        score_min = global_score_min

    return dict(
        selected_subgenres=selected_subgenres,
        selected_languages=selected_languages,
        selected_color=selected_color,
        sort=sort,
        year_min=year_min,
        year_max=year_max,
        score_min=score_min,
    )


def _apply_filters(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Apply filter params to a DataFrame and return it sorted."""
    filtered = df.copy()
    if params["selected_subgenres"]:
        filtered = filtered[filtered["Genre"].apply(
            lambda gs: isinstance(gs, list) and any(g in params["selected_subgenres"] for g in gs)
        )]
    if params["year_min"] is not None:
        filtered = filtered[filtered["Release Year"] >= params["year_min"]]
    if params["year_max"] is not None:
        filtered = filtered[filtered["Release Year"] <= params["year_max"]]
    filtered = filtered[filtered["Score"] >= params["score_min"]]
    if params["selected_languages"]:
        filtered = filtered[filtered["Language"].isin(params["selected_languages"])]
    if params["selected_color"]:
        filtered = filtered[filtered["Color"] == params["selected_color"]]

    sort = params.get("sort", "created")
    if sort == "best":
        return filtered.sort_values(
            by=["Score", "Overall", "Production", "Lyrics/Novelty", "Masterpiece Tracks"],
            ascending=[False, False, False, False, False],
            na_position="last",
        ).reset_index(drop=True)
    elif sort == "worst":
        return filtered.sort_values(
            by=["Score", "Overall", "Production", "Lyrics/Novelty", "Masterpiece Tracks"],
            ascending=[True, True, True, True, True],
            na_position="last",
        ).reset_index(drop=True)
    else:  # "created" (default)
        return filtered.sort_values("Created", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    df = get_data()
    if df.empty:
        return render_template("index.html", error=_load_error or "Impossibile caricare i dati.",
                               new_releases_italy=[], new_releases_world=[], albums_archive=[],
                               n_albums=0, n_artists=0, n_this_year=0,
                               delta_albums_added=None, delta_this_year=None,
                               added_this_year=0, pct_albums_change=None,
                               n_genres=0, avg_score=None,
                               delta_artists_added=None, pct_artists_change=None,
                               top_ranking=[], genre_cards=[],
                               current_year=datetime.now().year, prev_year=datetime.now().year - 1)

    current_year = datetime.now().year
    prev_year = current_year - 1

    # Stat cards
    n_albums = len(df)
    n_artists = int(df["Artist"].nunique())
    this_year_mask = df["Release Year"] == current_year
    n_this_year = int(this_year_mask.sum())

    # Deltas for stat cards
    added_this_year = int((df["Created"].dt.year == current_year).sum())
    added_prev_year = int((df["Created"].dt.year == prev_year).sum())
    delta_albums_added = added_this_year - added_prev_year

    n_prev_year_releases = int((df["Release Year"] == prev_year).sum())
    delta_this_year = n_this_year - n_prev_year_releases

    # Additional homepage stats
    # Distinct raw genre tags
    n_genres = len(set(
        g for genres_list in df["Genre"].dropna()
        if isinstance(genres_list, list)
        for g in genres_list
        if g
    ))

    # Average score
    score_series = df["Score"].dropna()
    avg_score = round(float(score_series.mean()), 1) if not score_series.empty else None

    # Percentage change in albums added this year vs prev year
    pct_albums_change = None
    if added_prev_year > 0:
        pct_albums_change = round((added_this_year - added_prev_year) / added_prev_year * 100)

    # Distinct artists in albums added this year vs prev year
    n_artists_added_this_year = int(df[df["Created"].dt.year == current_year]["Artist"].nunique())
    n_artists_added_prev_year = int(df[df["Created"].dt.year == prev_year]["Artist"].nunique())
    delta_artists_added = n_artists_added_this_year - n_artists_added_prev_year
    pct_artists_change = None
    if n_artists_added_prev_year > 0:
        pct_artists_change = round((n_artists_added_this_year - n_artists_added_prev_year) / n_artists_added_prev_year * 100)

    # Top 5 ranking
    top5_df = df.sort_values(
        by=["Score", "Masterpiece Tracks", "Release Year"],
        ascending=[False, False, True],
    ).head(5)
    top_ranking = [_row_to_dict(row) for _, row in top5_df.iterrows()]

    # Carousel 1a/1b: latest two release years, split by language, ordered by Created desc
    # Case-insensitive comparison to guard against casing inconsistencies in source data
    italy_df = df[df["Language"].str.lower() == "italiano"]
    world_df = df[df["Language"].str.lower() != "italiano"]

    italy_latest = get_latest_release_year(italy_df)
    world_latest = get_latest_release_year(world_df)

    def _recent_releases(subset: pd.DataFrame, latest_year: int | None) -> list:
        if latest_year is None or subset.empty:
            return []
        mask = subset["Release Year"].isin([latest_year, latest_year - 1])
        return [
            _row_to_dict(row)
            for _, row in subset[mask].sort_values("Created", ascending=False).head(20).iterrows()
        ]

    new_releases_italy = _recent_releases(italy_df, italy_latest)
    new_releases_world = _recent_releases(world_df, world_latest)

    # Carousel 2: archive (previous years), ordered by Created desc
    albums_archive_df = (
        df[~this_year_mask]
        .sort_values("Created", ascending=False)
        .head(20)
    )
    albums_archive = [_row_to_dict(row) for _, row in albums_archive_df.iterrows()]

    # Genre carousel
    genre_cards = get_genre_cards(df)

    # Non-Italian languages for the "Hot New Releases dal Mondo" Esplora link
    non_italian_languages = sorted([
        x for x in df["Language"].dropna().unique()
        if str(x).strip() and str(x).strip().lower() != "italiano"
    ])

    # Esplora year bounds: replicate exactly the release_year filters used per carousel.
    # Carousel 1 (Italy): Release Year ∈ [italy_latest - 1, italy_latest]
    italia_anno_min = (italy_latest - 1) if italy_latest is not None else None
    italia_anno_max = italy_latest

    # Carousel 2 (World): Release Year ∈ [world_latest - 1, world_latest]
    mondo_anno_min = (world_latest - 1) if world_latest is not None else None
    mondo_anno_max = world_latest

    # Carousel 3 (Archive): Release Year != current_year → anno_max = current_year - 1
    crate_max_year = current_year - 1

    return render_template(
        "index.html",
        error=None,
        n_albums=n_albums,
        n_artists=n_artists,
        n_this_year=n_this_year,
        delta_albums_added=delta_albums_added,
        delta_this_year=delta_this_year,
        added_this_year=added_this_year,
        pct_albums_change=pct_albums_change,
        n_genres=n_genres,
        avg_score=avg_score,
        delta_artists_added=delta_artists_added,
        pct_artists_change=pct_artists_change,
        top_ranking=top_ranking,
        genre_cards=genre_cards,
        new_releases_italy=new_releases_italy,
        new_releases_world=new_releases_world,
        albums_archive=albums_archive,
        current_year=current_year,
        prev_year=prev_year,
        non_italian_languages=non_italian_languages,
        italia_anno_min=italia_anno_min,
        italia_anno_max=italia_anno_max,
        mondo_anno_min=mondo_anno_min,
        mondo_anno_max=mondo_anno_max,
        crate_max_year=crate_max_year,
    )


@app.route("/genere/<path:genre_name>")
def genere(genre_name):
    df = get_data()
    if df.empty:
        return render_template(
            "genere.html",
            error=_load_error or "Impossibile caricare i dati.",
            genre_name=genre_name, albums=[],
            all_subgenres=[], all_years=[], all_languages=[], all_colors=[],
            all_languages_global=[],
            score_min=0, global_score_min=0, global_score_max=100,
            selected_subgenres=[], selected_languages=[], selected_color="",
            sort="created", year_min=None, year_max=None,
        )

    genre_df = df[df["unique_genre"] == genre_name]
    opts = _build_filter_options(genre_df)
    params = _read_filter_params(opts, default_year_to_max=False)
    filtered = _apply_filters(genre_df, params)
    albums = [_row_to_dict(row) for _, row in filtered.iterrows()]

    # All languages from the full dataset (for the language pill row)
    all_languages_global = sorted([x for x in df["Language"].dropna().unique() if str(x).strip()])

    return render_template(
        "genere.html",
        error=None,
        genre_name=genre_name,
        genre_description=GENRE_DESCRIPTIONS.get(genre_name),
        albums=albums,
        all_languages_global=all_languages_global,
        **opts,
        **params,
    )


@app.route("/archivio")
def archivio():
    df = get_data()
    if df.empty:
        return render_template(
            "archivio.html",
            error=_load_error or "Impossibile caricare i dati.",
            albums=[],
            all_subgenres=[], all_years=[], all_languages=[], all_colors=[],
            all_languages_global=[],
            score_min=0, global_score_min=0, global_score_max=100,
            selected_subgenres=[], selected_languages=[], selected_color="",
            sort="created", year_min=None, year_max=None,
        )

    opts = _build_filter_options(df)
    params = _read_filter_params(opts, default_year_to_max=False)
    filtered = _apply_filters(df, params)
    albums = [_row_to_dict(row) for _, row in filtered.iterrows()]
    all_languages_global = sorted([x for x in df["Language"].dropna().unique() if str(x).strip()])

    return render_template(
        "archivio.html",
        error=None,
        albums=albums,
        all_languages_global=all_languages_global,
        **opts,
        **params,
    )


@app.route("/search")
def search():
    df = get_data()
    query = request.args.get("q", "").strip()
    albums = []
    error = None

    if df.empty:
        error = _load_error or "Impossibile caricare i dati."
    elif query:
        mask = (
            df["Name"].str.contains(query, case=False, na=False)
            | df["Artist"].str.contains(query, case=False, na=False)
        )
        result = df[mask].sort_values("Release Year", ascending=False)
        albums = [_row_to_dict(row) for _, row in result.iterrows()]

    return render_template("search.html", query=query, albums=albums, error=error)


@app.route("/random")
def random_albums():
    df = get_data()
    error = None
    albums = []

    if df.empty:
        error = _load_error or "Impossibile caricare i dati."
        all_genres, all_years = [], []
        all_languages, all_colors = [], []
        score_min = 0
        global_score_min, global_score_max = 0, 100
        selected_genres, year_min, year_max = [], None, None
        selected_language, selected_color = "", ""
        generated = False
    else:
        all_genres = sorted(df["unique_genre"].dropna().unique())
        all_years = sorted([int(y) for y in df["Release Year"].dropna().unique()], reverse=True)
        all_languages = sorted([x for x in df["Language"].dropna().unique() if str(x).strip()])
        all_colors = sorted([x for x in df["Color"].dropna().unique() if str(x).strip()])
        global_score_min = int(df["Score"].min())
        global_score_max = int(df["Score"].max())

        selected_genres = request.args.getlist("genre")
        selected_language = request.args.get("language", "")
        selected_color = request.args.get("color", "")
        try:
            year_min = int(request.args.get("year_min", ""))
        except (ValueError, TypeError):
            year_min = None
        try:
            year_max = int(request.args.get("year_max", ""))
        except (ValueError, TypeError):
            year_max = None
        try:
            score_min = int(request.args.get("score_min", global_score_min))
        except (ValueError, TypeError):
            score_min = global_score_min

        generated = "generate" in request.args

        if generated:
            filtered = df.copy()
            if selected_genres:
                filtered = filtered[filtered["unique_genre"].isin(selected_genres)]
            if year_min is not None:
                filtered = filtered[filtered["Release Year"] >= year_min]
            if year_max is not None:
                filtered = filtered[filtered["Release Year"] <= year_max]
            filtered = filtered[filtered["Score"] >= score_min]
            if selected_language:
                filtered = filtered[filtered["Language"] == selected_language]
            if selected_color:
                filtered = filtered[filtered["Color"] == selected_color]

            sample_size = min(12, len(filtered))
            if sample_size > 0:
                sampled = filtered.sample(n=sample_size, replace=False)
                albums = [_row_to_dict(row) for _, row in sampled.iterrows()]

    return render_template(
        "random.html",
        error=error,
        albums=albums,
        all_genres=all_genres,
        all_years=all_years,
        all_languages=all_languages,
        all_colors=all_colors,
        selected_genres=selected_genres,
        selected_language=selected_language if not df.empty else "",
        selected_color=selected_color if not df.empty else "",
        year_min=year_min if not df.empty else None,
        year_max=year_max if not df.empty else None,
        score_min=score_min if not df.empty else 0,
        global_score_min=global_score_min if not df.empty else 0,
        global_score_max=global_score_max if not df.empty else 100,
        generated=generated,
    )


@app.route("/album/<slug>")
def album_detail(slug):
    df = get_data()
    if df.empty:
        return render_template("album_detail.html", error=_load_error or "Impossibile caricare i dati.",
                               album=None, other_scores=[]), 404
    matches = df[df["slug"] == slug]
    if matches.empty:
        return render_template("album_detail.html", error="Album non trovato.",
                               album=None, other_scores=[]), 404
    row = matches.iloc[0]
    album = _row_to_dict(row)
    # Attach other_scores values so the template can read them by column name
    for score_conf in _other_scores:
        col = score_conf["name"].lower().replace(" ", "_")
        raw = row.get(col)
        try:
            album[col] = float(raw) if pd.notna(raw) else None
        except (TypeError, ValueError):
            album[col] = None
    return render_template("album_detail.html", album=album, error=None, other_scores=_other_scores)


@app.route("/stats")
def stats():
    df = get_data()

    # Filter options always from the full unfiltered DataFrame
    all_languages = sorted([x for x in df["Language"].dropna().unique() if str(x).strip()])
    all_years = sorted([int(y) for y in df["Release Year"].dropna().unique()], reverse=True)

    # Active filter values from query params
    selected_language = request.args.get("language", "")
    try:
        selected_year = int(request.args.get("year", ""))
    except (ValueError, TypeError):
        selected_year = None

    # Slice the DataFrame before passing to stat functions
    filtered = df
    if selected_language:
        filtered = filtered[filtered["Language"] == selected_language]
    if selected_year is not None:
        filtered = filtered[filtered["Release Year"] == selected_year]

    return render_template(
        "stats.html",
        summary=get_summary_stats(filtered),
        tier_distribution=get_tier_distribution(filtered),
        albums_per_year=get_albums_per_year(filtered),
        genre_breakdown=get_genre_breakdown(filtered),
        artist_spotlight=get_artist_spotlight(filtered),
        subgenre_scatter=get_subgenre_scatter(filtered),
        all_languages=all_languages,
        all_years=all_years,
        selected_language=selected_language,
        selected_year=selected_year,
    )


@app.route("/perche")
def perche():
    return render_template("perche.html")


if __name__ == "__main__":
    app.run(debug=True)
