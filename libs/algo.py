"""libs/algo.py — Crateometro matching algorithms.

Isolated from app.py so the route stays thin and the matching logic
can be tested, extended, or swapped independently of Flask code.
"""

import math

import pandas as pd

# The 5 sonic dimension column names as stored in the DataFrame.
DIMENSIONS = ["Energy", "Emotional Weight", "Density", "Temperature", "Vastness"]

# Minimum Score for a candidate album to be considered.
MIN_SCORE = 60

# Maximum albums returned by euclidean_match.
MAX_RESULTS = 10

# Maximum albums per unique_genre bucket in the result set (genre diversity cap).
MAX_PER_GENRE = 2

# Theoretical maximum Euclidean distance over 5 dimensions (each ranging 1–5).
# Worst case: user = [1,1,1,1,1], album = [5,5,5,5,5] → sqrt(5 × 4²) ≈ 8.944.
_MAX_DISTANCE = math.sqrt(len(DIMENSIONS) * (5 - 1) ** 2)


def euclidean_match(user_values: dict, df: pd.DataFrame) -> list:
    """Return the albums whose 5-dimension sonic profile most closely matches user_values.

    The matching is based on the Euclidean distance between the user's
    profile vector and each album's profile vector in the 5-dimension space
    (Energy, Emotional Weight, Density, Temperature, Vastness).

    Only albums where all 5 dimensions are populated and whose Score is at
    least MIN_SCORE are eligible.  The distance-sorted pool is then filtered
    by a genre diversity cap (at most MAX_PER_GENRE albums per unique_genre
    bucket) before results are capped at MAX_RESULTS.

    Parameters
    ----------
    user_values : dict
        Maps each field in DIMENSIONS to an int 1–5, e.g.
        {"Energy": 3, "Emotional Weight": 4, "Density": 2,
         "Temperature": 5, "Vastness": 1}.
    df : pd.DataFrame
        The published album DataFrame produced by _load_data() in app.py.

    Returns
    -------
    list[dict]
        Up to MAX_RESULTS dicts, each containing:
          - ``slug``              (str)   album URL slug
          - ``distance``         (float) Euclidean distance, 0.0 – ~8.944
          - ``compatibility_pct``(int)   0–100, derived from normalised distance
          - ``score``            (float) album Score (0 if unavailable)
          - ``unique_genre``     (str)   mapped genre label (empty string if null)
        Sorted by descending compatibility_pct, then descending score.
    """
    if df is None or df.empty:
        return []

    # Keep only albums where all 5 dimensions are non-null.
    pool = df.copy()
    for field in DIMENSIONS:
        pool = pool[pool[field].notna()]

    # Apply minimum score threshold.
    pool = pool[pd.to_numeric(pool["Score"], errors="coerce") >= MIN_SCORE]

    if pool.empty:
        return []

    def _distance(row) -> float:
        return math.sqrt(
            sum((int(row[f]) - int(user_values[f])) ** 2 for f in DIMENSIONS)
        )

    pool = pool.copy()
    pool["_distance"] = pool.apply(_distance, axis=1)
    sorted_pool = pool.sort_values("_distance")

    # Genre diversity cap: iterate best-first and admit at most MAX_PER_GENRE
    # albums per unique_genre bucket.  Albums with no genre are grouped as
    # "unknown" and share the same cap.
    genre_counts: dict = {}
    results = []
    for _, row in sorted_pool.iterrows():
        if len(results) >= MAX_RESULTS:
            break
        genre_bucket = str(row.get("unique_genre") or "").strip() or "unknown"
        if genre_counts.get(genre_bucket, 0) >= MAX_PER_GENRE:
            continue
        genre_counts[genre_bucket] = genre_counts.get(genre_bucket, 0) + 1

        dist = float(row["_distance"])
        compat_pct = max(0, round((1.0 - dist / _MAX_DISTANCE) * 100))
        score = float(pd.to_numeric(row.get("Score"), errors="coerce") or 0)
        results.append({
            "slug": str(row.get("slug", "")),
            "distance": round(dist, 3),
            "compatibility_pct": compat_pct,
            "score": score,
            "unique_genre": str(row.get("unique_genre") or ""),
        })

    results.sort(key=lambda r: (-r["compatibility_pct"], -r["score"]))
    return results


if __name__ == "__main__":
    import json
    import sqlite3
    import sys
    from pathlib import Path

    # Ensure the project root is on sys.path so `libs.utils` is importable
    # when this file is run directly as `python3 libs/algo.py`.
    sys.path.insert(0, str(Path(__file__).parent.parent))

    def _usage():
        print(
            "Usage: python3 libs/algo.py <e> <ew> <d> <t> <v> [N]\n"
            "\n"
            "  e    Energy           1–5\n"
            "  ew   Emotional Weight 1–5\n"
            "  d    Density          1–5\n"
            "  t    Temperature      1–5\n"
            "  v    Vastness         1–5\n"
            "  N    max results      (optional, default 10)\n"
        )
        sys.exit(1)

    args = sys.argv[1:]
    if len(args) < 5 or len(args) > 6:
        _usage()

    try:
        dim_args = [int(a) for a in args[:5]]
        if any(not (1 <= v <= 5) for v in dim_args):
            raise ValueError("dimension values must be 1–5")
        if len(args) == 6:
            MAX_RESULTS = int(args[5])
    except (ValueError, IndexError):
        _usage()

    user_values = dict(zip(DIMENSIONS, dim_args))

    # Load the DataFrame — minimal replication of _load_data() from app.py.
    db_path = Path("albums.db")
    if not db_path.exists():
        print(f"Error: '{db_path}' not found. Run from the project root.", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    df_cli = pd.read_sql_query("SELECT * FROM albums", conn)
    conn.close()

    df_cli["Genre"] = df_cli["Genre"].apply(
        lambda x: json.loads(x) if isinstance(x, str) else []
    )
    df_cli = df_cli[df_cli["Published"] == True].reset_index(drop=True)

    try:
        from libs.utils import Utils, slugify
        df_cli["unique_genre"] = df_cli["Genre"].apply(Utils.map_genres)
        df_cli["slug"] = df_cli.apply(
            lambda r: slugify(str(r.get("Artist", "")) + " " + str(r.get("Name", ""))),
            axis=1,
        )
    except Exception as exc:
        print(f"Warning: could not derive unique_genre/slug: {exc}", file=sys.stderr)
        df_cli["unique_genre"] = ""
        df_cli["slug"] = ""

    results = euclidean_match(user_values, df_cli)

    if not results:
        print("No results found.")
        sys.exit(0)

    slug_idx = df_cli.set_index("slug") if "slug" in df_cli.columns else None

    col_w = (3, 25, 35, 6, 18, 7, 6, 6)
    header = (
        f"{'#':<{col_w[0]}} {'Artist':<{col_w[1]}} {'Album':<{col_w[2]}} "
        f"{'Year':<{col_w[3]}} {'Genre':<{col_w[4]}} {'Compat':>{col_w[5]}} "
        f"{'Score':>{col_w[6]}} {'Dist':>{col_w[7]}}"
    )
    print(header)
    print("─" * len(header))

    for i, r in enumerate(results, 1):
        row_data = None
        if slug_idx is not None and r["slug"] in slug_idx.index:
            hit = slug_idx.loc[r["slug"]]
            row_data = hit.iloc[0] if isinstance(hit, pd.DataFrame) else hit

        artist = str(row_data.get("Artist", "") if row_data is not None else "")[:col_w[1]]
        name   = str(row_data.get("Name",   "") if row_data is not None else r["slug"])[:col_w[2]]
        yr_raw = (row_data.get("Release Year", "") if row_data is not None else "")
        try:
            year = str(int(yr_raw)) if yr_raw and not pd.isna(yr_raw) else ""
        except (ValueError, TypeError):
            year = ""
        genre  = (r["unique_genre"] or "—")[:col_w[4]]

        print(
            f"{i:<{col_w[0]}} {artist:<{col_w[1]}} {name:<{col_w[2]}} "
            f"{year:<{col_w[3]}} {genre:<{col_w[4]}} "
            f"{r['compatibility_pct']:>{col_w[5]-1}}% "
            f"{r['score']:>{col_w[6]}.1f} {r['distance']:>{col_w[7]}.3f}"
        )
