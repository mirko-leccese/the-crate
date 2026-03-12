import html
import math
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
    return Utils.read_image_as_data_uri(candidate)


st.set_page_config(
    page_title="Random Album Generator",
    page_icon="🎲",
    layout="wide"
)

with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

with st.sidebar:
    st.page_link('main.py', label='Home', icon='🏠')
    st.page_link('pages/top_albums.py', label='Top Album', icon='🏆')
    st.page_link('pages/lists.py', label='Lists', icon="📋")
    st.page_link('pages/search.py', label='Rating Search', icon='🔍')
    st.page_link('pages/random.py', label='Random Generator', icon='#️⃣')
    st.page_link('pages/stats.py', label='Rating Stats', icon='📊')
    st.page_link('pages/perche.py', label='Perché?', icon='💬')

if "album_df" not in st.session_state:
    st.error("⚠️ Dataset non caricato. Torna alla home.")
    st.stop()

df = st.session_state.album_df.copy()

st.markdown("<h1 class='page-title'>Random Album Generator</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='color:#6B7280; font-size:0.95rem; margin: -0.4rem 0 1.2rem;'>"
    "Filtra → genera → lasciati sorprendere."
    "</p>",
    unsafe_allow_html=True,
)

# --- Filtri ---
all_genres = ["Tutti i generi"] + sorted(df["unique_genre"].dropna().unique())
all_languages = ["Tutte le lingue"] + sorted(df["Language"].dropna().unique())
all_colors = ["Tutti i colori"] + sorted(df["Color"].dropna().unique())
all_years = sorted(df["Release Year"].dropna().unique())
all_tiers = sorted(df["Tier"].dropna().unique())

r1 = st.columns(3)
with r1[0]:
    selected_genres = st.multiselect("🎧 Genere", all_genres, default=["Tutti i generi"])
with r1[1]:
    selected_language = st.selectbox("🌐 Lingua", all_languages)
with r1[2]:
    selected_color = st.selectbox("🖍️ Colore", all_colors)

r2 = st.columns(3)
with r2[0]:
    selected_years = st.multiselect("📅 Anno di Uscita", all_years)
with r2[1]:
    selected_tiers = st.multiselect("🏷️ Tier", all_tiers)
with r2[2]:
    grid_size = st.slider("🔢 Dimensione griglia (NxN)", 1, 5, 3)

# --- Applica filtri ---
filtered_df = df.copy()

if "Tutti i generi" not in selected_genres:
    filtered_df = filtered_df[filtered_df["unique_genre"].isin(selected_genres)]

if selected_language != "Tutte le lingue":
    filtered_df = filtered_df[filtered_df["Language"] == selected_language]

if selected_color != "Tutti i colori":
    filtered_df = filtered_df[filtered_df["Color"] == selected_color]

if selected_years:
    filtered_df = filtered_df[filtered_df["Release Year"].isin(selected_years)]

if selected_tiers:
    filtered_df = filtered_df[filtered_df["Tier"].isin(selected_tiers)]

# --- Pulsante Genera ---
_, col_btn, _ = st.columns([2, 1, 2])
with col_btn:
    generate = st.button("🎲 Genera", use_container_width=True)

# --- Griglia ---
if generate:
    total = grid_size * grid_size
    sampled = filtered_df.sample(
        n=min(total, len(filtered_df)),
        replace=False
    )

    album_iter = sampled.iterrows()
    rows = math.ceil(total / grid_size)

    st.markdown("<div class='random-grid-wrapper'>", unsafe_allow_html=True)

    for _ in range(rows):
        st.markdown("<div style='margin-bottom: 1.2rem;'>", unsafe_allow_html=True)
        cols = st.columns(grid_size, gap="medium")
        for col in cols:
            with col:
                try:
                    _, album = next(album_iter)
                    src = _get_cover_src(album["final_cover"])
                    if src:
                        st.markdown(
                            f"<img src='{src}' class='random-album-cover'/>",
                            unsafe_allow_html=True
                        )
                except StopIteration:
                    st.markdown("<div class='random-album-empty'></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
