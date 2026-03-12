from libs.notion import NotionClient
from libs.utils import Utils
from libs.getdb import extract_album_info

import html as _html
import json
import os
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd


def _resolve_cover_for_html(final_cover) -> str:
    """Return a src string (URL or data URI) suitable for use in an <img> tag."""
    if not final_cover or not isinstance(final_cover, str):
        return ""
    cover = final_cover.strip()
    if not cover:
        return ""
    if cover.startswith("http://") or cover.startswith("https://"):
        return _html.escape(cover)
    path = Path(cover)
    if not path.is_absolute():
        path = Path.cwd() / path
    return Utils.read_image_as_data_uri(path) or ""


def _build_shelf(df: pd.DataFrame, title: str, subtitle: str = "") -> str:
    """Build an Apple-Music-style horizontal scrollable shelf as an HTML string."""
    cards = []
    for _, row in df.iterrows():
        src = _resolve_cover_for_html(row.get("final_cover"))
        if src:
            img = f"<img class='shelf-card__cover' src='{src}' loading='lazy' alt=''>"
        else:
            img = "<div class='shelf-card__cover shelf-card__cover--placeholder'></div>"

        name = _html.escape(str(row.get("Name") or ""))
        artist = _html.escape(str(row.get("Artist") or ""))

        # Artist | Release Date (formatted as "Mar 2024")
        release_date = row.get("Release Date")
        date_str = ""
        if release_date is not None and not (isinstance(release_date, float) and pd.isna(release_date)):
            try:
                if hasattr(release_date, "strftime"):
                    date_str = f" | {release_date.day} {release_date.strftime('%b %Y')}"
                elif isinstance(release_date, str) and release_date:
                    date_obj = datetime.strptime(release_date[:10], "%Y-%m-%d")
                    date_str = f" | {date_obj.day} {date_obj.strftime('%b %Y')}"
            except (ValueError, AttributeError):
                pass
        artist_line = f"{artist}{date_str}"

        # Unique genre tag (single)
        unique_genre = row.get("unique_genre")
        genre_html = (
            f"<div class='shelf-card__genres'><span class='shelf-card__genre'>{_html.escape(str(unique_genre))}</span></div>"
            if unique_genre and pd.notna(unique_genre)
            else ""
        )

        # Score chip: star + score/100 · Tier · Rank all on one line
        score = row.get("Score")
        tier = row.get("Tier")
        rank = row.get("Rank")
        if score is not None and not pd.isna(score):
            score_int = int(score)
            star = "⭐ " if score_int >= 85 else ""
            parts = [f"{star}{score_int}/100"]
            if tier is not None and not pd.isna(tier):
                parts.append(f"Tier {int(tier)}°")
            if rank is not None and not pd.isna(rank):
                parts.append(f"Rank {int(rank)}°")
            chip = f"<div class='shelf-card__chip'>{' · '.join(parts)}</div>"
        else:
            chip = ""

        cards.append(f"""
        <div class="shelf-card">
            {img}
            <div class="shelf-card__info">
                <div class="shelf-card__name">{name}</div>
                <div class="shelf-card__artist">{artist_line}</div>
                {genre_html}
                {chip}
            </div>
        </div>""")

    subtitle_html = (
        f"<p class='shelf__subtitle'>{_html.escape(subtitle)}</p>" if subtitle else ""
    )
    return f"""
    <hr class='shelf-divider'>
    <div class="shelf">
        <div class="shelf__header">
            <h2 class="shelf__title">{_html.escape(title)}</h2>
            {subtitle_html}
        </div>
        <div class="shelf__track">{"".join(cards)}</div>
    </div>
    <hr class='shelf-divider'>"""


def main():

    # Read Notion config (local file if present, otherwise Streamlit secrets / env vars)
    if Path("notion-keys.json").exists():
        with open("notion-keys.json", "r") as f:
            notion_keys = json.load(f)
        notion_token = notion_keys["NOTION_TOKEN"]
        rating_db_id = notion_keys["RATING_DATABASE_ID"]
    else:
        notion_token = st.secrets.get("NOTION_TOKEN") or os.environ["NOTION_TOKEN"]
        rating_db_id = st.secrets.get("RATING_DATABASE_ID") or os.environ["RATING_DATABASE_ID"]

    # create instance of NotionClient
    notion_client = NotionClient(NOTION_TOKEN=notion_token)

    # Get DB
    album_db = notion_client.get_db_pages(DATABASE_ID=rating_db_id)

    # Load album data
    albums_data = [extract_album_info(page) for page in album_db]

    # Query Dataframe
    album_df = pd.DataFrame(albums_data)

    # Only show published albums
    album_df = album_df[album_df["Published"] == True].reset_index(drop=True)

    # Apply post-processing
    album_df["unique_genre"] = album_df["Genre"].apply(lambda x: Utils.map_genres(x))
    # Sort by the required columns (descending for numeric ones, ascending for alphabet)
    #album_df['p_Good'] = album_df['Good Tracks']/album_df['Total Tracks']
    album_df = album_df.sort_values(
        by=['Score', 'Lyrics/Novelty', 'Production',  'Masterpiece Tracks', 'Name'],
        ascending=[False, False, False,  False, True]
    ).reset_index(drop=True)

    # Create an album cover column using link or image
    def get_cover(row):
        if pd.notna(row["Picname"]):
            return f"artworks/{row['Picname']}"
        else:
            return row["Cover"]

    album_df["final_cover"] = album_df.apply(get_cover, axis=1)

    # Parse Created datetime
    album_df["Created"] = pd.to_datetime(album_df["Created"], utc=True, errors="coerce")

    # Parse Release Date as datetime
    if "Release Date" not in album_df.columns:
        album_df["Release Date"] = pd.NaT
    album_df["Release Date"] = pd.to_datetime(album_df["Release Date"], errors="coerce")

    # Add a global ranking column starting from 1
    album_df['Rank'] = album_df.index + 1

    # Add Tier 
    tier_bins = [0, 49, 59, 69, 74, 84, 89, 95, 100]
    tier_labels = [8, 7, 6, 5, 4, 3, 2, 1]  # Fascia 1 = migliore
    album_df["Tier"] = pd.cut(album_df["Score"], bins=tier_bins, labels=tier_labels, right=True, include_lowest=True)
    album_df["Tier"] = album_df["Tier"].astype(int)  # converte da categoria a intero

    # Evita di ricaricare il DataFrame ad ogni refresh
    if "album_df" not in st.session_state:
        st.session_state.album_df = album_df

    st.set_page_config(page_title="Dashboard Album", page_icon="🎶", layout="wide")

    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    # --- Sidebar Navigation ---------
    with st.sidebar:
        st.page_link('main.py', label='Home', icon='🏠')
        st.page_link('pages/top_albums.py', label='Top Album', icon='🏆')
        st.page_link('pages/lists.py', label='Lists', icon="📋")
        st.page_link('pages/search.py', label='Rating Search', icon='🔍')
        st.page_link('pages/random.py', label='Random Generator', icon='#️⃣')
        st.page_link('pages/stats.py', label='Rating Stats', icon='📊')
        st.page_link('pages/perche.py', label='Perché?', icon='💬')

    # --- Home Page ---
    st.markdown("<h1 class='home-title'>The Crate</h1>", unsafe_allow_html=True)

    df = st.session_state.album_df

    current_year = datetime.now().year

    # Shelf 1: 20 most recently released albums from current or previous year
    recent_years = [current_year, current_year - 1]
    recently_added = (
        df[df["Release Year"].isin(recent_years)]
        .sort_values("Release Date", ascending=False)
        .head(20)
    )
    st.markdown(_build_shelf(recently_added, "Nuove Uscite", "I 20 album più recenti nella collezione"), unsafe_allow_html=True)

    st.markdown('<hr style="border: 1px solid #D1D5DB; margin: 2rem 0;">', unsafe_allow_html=True)

    # Shelf 2: 20 most recently added albums, excluding current-year releases
    back_catalog = (
        df[df["Release Year"] != current_year]
        .sort_values("Created", ascending=False)
        .head(20)
    )
    st.markdown(_build_shelf(back_catalog, "Dal passato", "Riscoperte dal catalogo storico"), unsafe_allow_html=True)

    # Stat cards
    n_albums = len(df)
    n_artists = df["Artist"].nunique()
    n_genres = len(set(df.explode("Genre")["Genre"].dropna()))
    stats_html = f"""
    <hr style="border: 1px solid #D1D5DB; margin: 2rem 0;">
    <div class="stat-cards">
        <div class="stat-card">
            <div class="stat-card__value">{n_albums}</div>
            <div class="stat-card__label">Album</div>
        </div>
        <div class="stat-card">
            <div class="stat-card__value">{n_artists}</div>
            <div class="stat-card__label">Artisti</div>
        </div>
        <div class="stat-card">
            <div class="stat-card__value">{n_genres}</div>
            <div class="stat-card__label">Generi</div>
        </div>
    </div>"""
    st.markdown(stats_html, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

