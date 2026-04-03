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

# Theoretical maximum Euclidean distance over 5 dimensions (each ranging 1–5).
# Worst case: user = [1,1,1,1,1], album = [5,5,5,5,5] → sqrt(5 × 4²) ≈ 8.944.
_MAX_DISTANCE = math.sqrt(len(DIMENSIONS) * (5 - 1) ** 2)


def euclidean_match(user_values: dict, df: pd.DataFrame) -> list:
    """Return the albums whose 5-dimension sonic profile most closely matches user_values.

    The matching is based on the Euclidean distance between the user's
    profile vector and each album's profile vector in the 5-dimension space
    (Energy, Emotional Weight, Density, Temperature, Vastness).

    Only albums where all 5 dimensions are populated and whose Score is at
    least MIN_SCORE are eligible.  Results are sorted by ascending distance
    (closest match first) and capped at MAX_RESULTS.

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
        Sorted by ascending distance (best match first).
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
    top = pool.sort_values("_distance").head(MAX_RESULTS)

    results = []
    for _, row in top.iterrows():
        dist = float(row["_distance"])
        compat_pct = max(0, round((1.0 - dist / _MAX_DISTANCE) * 100))
        results.append({
            "slug": str(row.get("slug", "")),
            "distance": round(dist, 3),
            "compatibility_pct": compat_pct,
        })
    return results
