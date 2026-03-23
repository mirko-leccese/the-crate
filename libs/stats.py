"""Stats page data computation — all functions receive the cached DataFrame
and return plain Python dicts/lists. No Flask, no rendering logic here."""

from datetime import datetime

import pandas as pd

from libs.utils import Utils


def get_latest_release_year(df: pd.DataFrame) -> int | None:
    """Return the highest Release Year present in *df*, or None if df is empty."""
    years = df["Release Year"].dropna()
    if years.empty:
        return None
    return int(years.max())


def get_summary_stats(df: pd.DataFrame) -> dict:
    """Returns top-level aggregate stats for the summary bar cards."""
    if df.empty:
        return {
            "n_albums": 0,
            "n_this_year": 0,
            "n_artists": 0,
            "n_genres": 0,
            "avg_score": None,
            "best_album_name": "",
            "best_album_artist": "",
        }

    current_year = datetime.now().year
    n_albums = len(df)
    n_this_year = int((df["Release Year"] == current_year).sum())
    n_artists = int(df["Artist"].nunique())

    n_genres = len({
        g
        for genres_list in df["Genre"].dropna()
        if isinstance(genres_list, list)
        for g in genres_list
        if g
    })

    score_series = df["Score"].dropna()
    avg_score = round(float(score_series.mean()), 1) if not score_series.empty else None

    valid = df.dropna(subset=["Score"])
    if not valid.empty:
        best_row = valid.sort_values(by=["Score", "Rank"], ascending=[False, True]).iloc[0]
        best_album_name = str(best_row.get("Name", ""))
        best_album_artist = str(best_row.get("Artist", ""))
    else:
        best_album_name = ""
        best_album_artist = ""

    return {
        "n_albums": n_albums,
        "n_this_year": n_this_year,
        "n_artists": n_artists,
        "n_genres": n_genres,
        "avg_score": avg_score,
        "best_album_name": best_album_name,
        "best_album_artist": best_album_artist,
    }


def get_tier_distribution(df: pd.DataFrame) -> list:
    """Returns album counts per Tier, sorted Tier 1 first, with bar width percentages and score-range labels."""
    if df.empty or "Tier" not in df.columns:
        return []

    counts = df["Tier"].dropna().astype(int).value_counts().to_dict()
    if not counts:
        return []

    max_count = max(counts.values())
    return [
        {
            "tier": tier,
            "label": f"Tier {tier} ({Utils.tier_score_range(tier)})",
            "count": counts[tier],
            "pct": round(counts[tier] / max_count * 100),
        }
        for tier in sorted(counts.keys())
    ]


def get_albums_per_year(df: pd.DataFrame) -> list:
    """Returns album counts for the latest 10 years with data, with bar height percentages."""
    if df.empty or "Release Year" not in df.columns:
        return []

    year_counts = (
        df["Release Year"]
        .dropna()
        .astype(int)
        .value_counts()
        .sort_index(ascending=True)
    )
    year_counts = year_counts[year_counts > 0]
    if len(year_counts) > 10:
        year_counts = year_counts.iloc[-10:]

    if year_counts.empty:
        return []

    max_count = int(year_counts.max())
    return [
        {
            "year": int(year),
            "count": int(count),
            "pct": round(int(count) / max_count * 100),
        }
        for year, count in year_counts.items()
    ]


def get_genre_breakdown(df: pd.DataFrame) -> dict:
    """Returns top macro genres by album count and by average score, using the unique_genre column."""
    if df.empty or "unique_genre" not in df.columns:
        return {"top_by_count": [], "top_by_avg_score": []}

    genre_series = df["unique_genre"].dropna()

    top_counts = genre_series.value_counts()
    top_by_count = [
        {"genre": genre, "count": int(count)}
        for genre, count in top_counts.items()
    ]

    genre_stats = (
        df.dropna(subset=["Score", "unique_genre"])
        .groupby("unique_genre")["Score"]
        .agg(["mean", "count"])
        .reset_index()
    )
    genre_stats.columns = ["genre", "avg_score", "n"]
    qualified = genre_stats[genre_stats["n"] >= 3]
    top_by_avg = qualified.sort_values("avg_score", ascending=False)
    top_by_avg_score = [
        {"genre": row["genre"], "avg_score": round(float(row["avg_score"]), 1)}
        for _, row in top_by_avg.iterrows()
    ]

    return {
        "top_by_count": top_by_count,
        "top_by_avg_score": top_by_avg_score,
    }


def get_artist_spotlight(df: pd.DataFrame) -> dict:
    """Returns most reviewed artists and highest rated artists (min 2 albums)."""
    if df.empty or "Artist" not in df.columns:
        return {"most_reviewed": [], "highest_rated": []}

    most_reviewed_vc = df["Artist"].dropna().value_counts().head(8)
    most_reviewed = [
        {"artist": artist, "count": int(count)}
        for artist, count in most_reviewed_vc.items()
    ]

    artist_stats = (
        df.dropna(subset=["Score", "Artist"])
        .groupby("Artist")["Score"]
        .agg(["mean", "count"])
        .reset_index()
    )
    artist_stats.columns = ["artist", "avg_score", "n"]
    qualified = artist_stats[artist_stats["n"] >= 2]
    top_rated = qualified.sort_values("avg_score", ascending=False).head(8)
    highest_rated = [
        {"artist": row["artist"], "avg_score": round(float(row["avg_score"]), 1)}
        for _, row in top_rated.iterrows()
    ]

    return {
        "most_reviewed": most_reviewed,
        "highest_rated": highest_rated,
    }


def get_genre_cards(df: pd.DataFrame) -> list:
    """Returns per-genre summary for the Esplora genre grid.

    Each entry has: genre name, album count, and the cover URL of the
    top-rated album in that genre (used as the card background image).
    """
    if df.empty or "unique_genre" not in df.columns:
        return []

    result = []
    for genre in sorted(df["unique_genre"].dropna().unique()):
        genre_df = df[df["unique_genre"] == genre]
        count = len(genre_df)
        valid = genre_df.dropna(subset=["Score"])
        if not valid.empty:
            top_row = valid.sort_values(
                by=["Score", "Rank"], ascending=[False, True]
            ).iloc[0]
            cover_url = str(top_row.get("cover_url", ""))
        else:
            cover_url = ""
        result.append({"genre": genre, "count": count, "cover_url": cover_url})

    return result


def get_subgenre_scatter(df: pd.DataFrame) -> list:
    """Returns score vs. count data for each subgenre, for scatter plot rendering."""
    if df.empty:
        return []

    # Build exclusion set from unique_genre values (normalized: lowercase + stripped)
    exclusion = {
        str(g).strip().lower()
        for g in df["unique_genre"].dropna()
    }

    # Collect (subgenre_tag, score) pairs, excluding macro genre labels
    rows = []
    for _, row in df.iterrows():
        genres = row.get("Genre", [])
        if not isinstance(genres, list):
            continue
        score = row.get("Score")
        seen_in_row: set = set()
        for g in genres:
            if not g:
                continue
            normalized = str(g).strip().lower()
            if normalized in exclusion or normalized in seen_in_row:
                continue
            seen_in_row.add(normalized)
            rows.append({"subgenre": str(g).strip(), "score": score})

    if not rows:
        return []

    sub_df = pd.DataFrame(rows)
    stats = (
        sub_df.dropna(subset=["score"])
        .groupby("subgenre")["score"]
        .agg(["mean", "count"])
        .reset_index()
    )
    stats.columns = ["name", "avg_score", "count"]
    qualified = stats[stats["count"] >= 2]

    return [
        {
            "name": row["name"],
            "count": int(row["count"]),
            "avg_score": round(float(row["avg_score"]), 1),
        }
        for _, row in qualified.iterrows()
    ]
