import html
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

from libs.utils import Utils


def _get_cover_src(raw_value) -> Optional[str]:
    if not isinstance(raw_value, str):
        return None
    cover_value = raw_value.strip()
    if not cover_value:
        return None
    if Utils.is_url(cover_value):
        return html.escape(cover_value)
    candidate = Path(cover_value)
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    data_uri = Utils.read_image_as_data_uri(candidate)
    return data_uri


def _coerce_float(value):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(numeric):
        return None
    return numeric


def _format_number(value, decimals=1):
    numeric = _coerce_float(value)
    if numeric is not None:
        return f"{numeric:.{decimals}f}"
    return "-"


def _safe_str(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    if isinstance(value, str):
        return value
    return str(value)


def _truncate_text(value: str, limit: int) -> tuple[str, bool]:
    if len(value) <= limit:
        return value, False
    truncated = value[:limit].rsplit(" ", 1)[0]
    if not truncated:
        truncated = value[:limit]
    return truncated.rstrip() + "...", True


def _render_notes_section(raw_notes, limit: int = 360) -> str:
    if raw_notes is None:
        return ""
    try:
        if pd.isna(raw_notes):
            return ""
    except TypeError:
        pass
    notes_str = _safe_str(raw_notes).strip()
    if not notes_str:
        return ""

    truncated_text, shortened = _truncate_text(notes_str, limit)
    truncated_html = html.escape(truncated_text).replace("\n", "<br>")
    full_html = html.escape(notes_str).replace("\n", "<br>")

    if not shortened:
        return f"<div class='album-notes album-notes--plain'>{full_html}</div>"

    return f"""
    <details class="album-notes">
        <summary>
            <span class="album-notes__summary-text">{truncated_html}</span>
            <span class="album-notes__toggle album-notes__toggle--show">Leggi tutto</span>
            <span class="album-notes__toggle album-notes__toggle--hide">Mostra meno</span>
        </summary>
        <div class="album-notes__full">{full_html}</div>
    </details>
    """.strip()


def _tier_badge_html(tier_value, global_rank_display, rating_numeric) -> str:
    # Tier 4+ → azzurro pastello con testo blu scuro
    tier_colors = {
        1: ("#FFD700", "#78350f"),
        2: ("#C0C0C0", "#1f2937"),
        3: ("#CD7F32", "#fff"),
    }
    try:
        tier_int = int(tier_value) if tier_value is not None and not pd.isna(tier_value) else None
    except (TypeError, ValueError):
        tier_int = None
    bg, fg = tier_colors.get(tier_int, ("#BFDBFE", "#1E40AF"))
    parts = []
    if tier_int:
        parts.append(f"Tier {tier_int}")
    if global_rank_display:
        parts.append(f"Rank {global_rank_display}°")
    if rating_numeric is not None:
        parts.append(f"{rating_numeric:.1f}/100")
    content = " · ".join(parts)
    return f"<div class='tier-badge' style='background:{bg};color:{fg};'>{content}</div>"


st.set_page_config(page_title="Top Album", page_icon="🏆", layout="wide")

with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("""
<style>
/* Expander label più grande */
div[data-testid="stExpander"] summary span p {
    font-size: 1.3rem !important;
    font-weight: 600 !important;
}

/* Slider: thumb */
div[data-testid="stSlider"] [role="slider"] {
    background: #3b82f6 !important;
    border-color: #3b82f6 !important;
    border-radius: 50% !important;
    box-shadow: 0 1px 5px rgba(59,130,246,0.45), 0 0 0 3px rgba(59,130,246,0.15) !important;
}
/* Slider: active track */
div[data-testid="stSlider"] div[data-baseweb="slider"] > div > div:nth-child(3) > div {
    background: #3b82f6 !important;
}
div[data-testid="stSlider"] div[data-baseweb="slider"] [class*="Track"]:nth-child(3) div {
    background: #3b82f6 !important;
}
/* Slider: numeric values */
div[data-testid="stSlider"] div[data-testid="stTickBarMin"],
div[data-testid="stSlider"] div[data-testid="stTickBarMax"] {
    color: #3b82f6 !important;
    font-weight: 600 !important;
}

/* score-details full-width */
.score-details--fullwidth {
    width: 100%;
    margin-top: 0.8rem;
}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.page_link('main.py', label='Home', icon='🏠')
    st.page_link('pages/top_albums.py', label='Top Album', icon='🏆')
    st.page_link('pages/lists.py', label='Lists', icon="📋")
    st.page_link('pages/search.py', label='Search Ratings', icon='🔍')
    st.page_link('pages/random.py', label='Random Generator', icon='#️⃣')
    st.page_link('pages/stats.py', label='Rating Stats', icon='📊')
    st.page_link('pages/perche.py', label='Perché?', icon='💬')

# Recupera il DataFrame caricato in main.py
if "album_df" not in st.session_state:
    st.error("⚠️ Dataset non caricato. Torna alla home per inizializzare i dati.")
else:
    df = st.session_state.album_df

st.markdown("<h1 class='page-title'>Top Album</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='color:#6B7280; font-size:0.95rem; margin: -0.4rem 0 1.2rem;'>"
    "🎵 Benvenuto nella classifica dei migliori album della collezione. Ogni disco è valutato su più dimensioni "
    "— dalla qualità produttiva ai testi — e collocato in un tier in base al punteggio complessivo. "
    "Usa i filtri per esplorare per anno, genere o artista e scoprire le gemme nascoste."
    "</p>",
    unsafe_allow_html=True,
)

# --- Filtri collassabili ---
all_years = ["Tutti gli anni"] + sorted(df["Release Year"].dropna().unique(), reverse=True)
all_languages = ["Tutte le lingue"] + sorted(df["Language"].dropna().unique())
all_colors = ["Tutti i colori"] + sorted(df["Color"].dropna().unique())
all_artists = sorted(df["Artist"].dropna().unique())
all_genres = ["Tutti i generi"] + sorted(df["unique_genre"].dropna().unique())
min_rating = int(df["Score"].min())
max_rating = int(df["Score"].max())
default_year = df["Release Year"].dropna().max()  # anno più recente nel dataset

with st.expander("🎛️ Filtri", expanded=False):
    col1, col2 = st.columns(2, gap="medium")
    with col1:
        selected_years = st.multiselect("📅 Anno di Uscita", options=all_years, default=[default_year])
    with col2:
        selected_language = st.selectbox("🌐 Lingua", options=all_languages)

    col3, col4 = st.columns(2, gap="medium")
    with col3:
        selected_color = st.selectbox("🖍️ Colore", options=all_colors)
    with col4:
        selected_artists = st.multiselect("🎤 Artisti", options=all_artists)

    col5, col6 = st.columns(2, gap="medium")
    with col5:
        selected_genres = st.multiselect("🎧 Generi", options=all_genres, default=["Tutti i generi"])

    if "Tutti i generi" in selected_genres or not selected_genres:
        temp_df = df.copy()
    else:
        temp_df = df[df["unique_genre"].isin(selected_genres)]
    available_subgenres = sorted({g for sublist in temp_df["Genre"] for g in sublist})

    with col6:
        selected_subgenres = st.multiselect("🎧 Sottogeneri", options=available_subgenres)

    selected_rating_range = st.slider(
        "🏆 Punteggio",
        min_value=min_rating,
        max_value=max_rating,
        value=(min_rating, max_rating)
    )

# --- Applica filtri ---
filtered_df = df.copy()

if selected_years and "Tutti gli anni" not in selected_years:
    filtered_df = filtered_df[filtered_df["Release Year"].isin(selected_years)]
if selected_language != "Tutte le lingue":
    filtered_df = filtered_df[filtered_df["Language"] == selected_language]
if selected_artists:
    filtered_df = filtered_df[filtered_df["Artist"].isin(selected_artists)]
if selected_genres and "Tutti i generi" not in selected_genres:
    filtered_df = filtered_df[filtered_df["unique_genre"].isin(selected_genres)]
if selected_subgenres:
    filtered_df = filtered_df[
        filtered_df["Genre"].apply(lambda genres: any(g in genres for g in selected_subgenres))
    ]
if selected_color != "Tutti i colori":
    filtered_df = filtered_df[filtered_df["Color"] == selected_color]
filtered_df = filtered_df[
    filtered_df["Score"].between(selected_rating_range[0], selected_rating_range[1])
]

st.divider()

# --- Ordina e mostra ---
sort_fields = ['Score', 'Lyrics/Novelty', 'Production', 'Masterpiece Tracks', 'Release Year', 'Name']
sort_order = [False, False, False, False, True, False]
top_N = 100
sorted_df = filtered_df.sort_values(sort_fields, ascending=sort_order).reset_index(drop=True).head(top_N)

podium_emojis = ["🥇", "🥈", "🥉"]

_, album_col, _ = st.columns([1, 4, 1])

with album_col:
    for i, row in sorted_df.iterrows():
        position = i + 1
        emoji = podium_emojis[i] if i < 3 else f"{position}°"
        special_tag = "✰" if bool(row.get("Special", False)) else ""
        title = html.escape(_safe_str(row.get("Name", "")))

        release_year = row.get("Release Year")
        release_year_display = (
            str(int(release_year))
            if isinstance(release_year, (int, float)) and pd.notna(release_year)
            else ""
        )
        title_suffix = f" ({release_year_display})" if release_year_display else ""

        global_rank = row.get("Rank")
        global_rank_display = (
            str(int(global_rank))
            if isinstance(global_rank, (int, float)) and pd.notna(global_rank)
            else ""
        )

        artist = html.escape(_safe_str(row.get("Artist", "")))

        genres_raw = row.get("Genre", [])
        if not isinstance(genres_raw, list):
            genres_raw = []
        tags_html = "".join(
            f"<span class='genre-tag'>{html.escape(str(genre))}</span>"
            for genre in genres_raw
            if pd.notna(genre)
        )
        tags_section = (
            f"<div class='album-tags'>{tags_html}</div>" if tags_html else ""
        )

        notes_raw = row.get("Notes", "")
        notes_section = _render_notes_section(notes_raw)

        rating_value = row.get("Score", 0)
        rating_numeric = _coerce_float(rating_value)

        tier_value = row.get("Tier")
        badge_html = _tier_badge_html(tier_value, global_rank_display, rating_numeric)

        cover_src = _get_cover_src(row.get("final_cover"))
        cover_html = (
            f'<img src="{cover_src}" alt="Cover of {title}">'
            if cover_src
            else '<div class="album-cover__placeholder">No Cover</div>'
        )

        overall = _format_number(row.get("Overall"), 1)
        production = _format_number(row.get("Production"), 1)
        lyrics = _format_number(row.get("Lyrics/Novelty"), 1)

        metrics = [
            ("🎧 Impressione Generale", f"{overall}/10"),
            ("🎛️ Produzione", f"{production}/3.0" if production != "-" else "-"),
            ("🧠 Voce/Testi", f"{lyrics}/3.0" if lyrics != "-" else "-"),
        ]
        metrics_html = "".join(
            f"<div><div class='metric-label'>{label}</div><div class='metric-value'>{html.escape(str(value))}</div></div>"
            for label, value in metrics
        )

        top_tracks_raw = _safe_str(row.get("Masterpiece Track Titles", "")).strip()
        top_tracks_html = (
            f"<p style='margin: 0.75rem 0 0; font-size:0.88rem; color:#3a3a3a;'>"
            f"🎵 <strong>Tracce top:</strong> {html.escape(top_tracks_raw)}"
            f"</p>"
            if top_tracks_raw else ""
        )

        # Struttura: riga superiore (cover | info) + riga inferiore full-width (dettaglio punteggi)
        card_html = f"""
        <div class="album-card">
            <div class="album-header">
                <h3>{emoji} | {title}{title_suffix}{f" {special_tag}" if special_tag else ""}</h3>
            </div>
            <div class="album-main">
                <div class="album-cover">
                    {cover_html}
                </div>
                <div class="album-info">
                    <div class="album-info__meta">
                        <p><strong>Artist:</strong> {artist}</p>
                    </div>
                    {tags_section}
                    {notes_section}
                    {badge_html}
                </div>
            </div>
            <details class="score-details score-details--fullwidth">
                <summary class="score-summary">
                    <span class="toggle-label toggle-label--show">📊 Dettaglio punteggi</span>
                    <span class="toggle-label toggle-label--hide">Nascondi punteggi</span>
                </summary>
                <div class="album-metrics">
                    {metrics_html}
                </div>
                {top_tracks_html}
            </details>
        </div>
        """

        st.markdown(card_html, unsafe_allow_html=True)
