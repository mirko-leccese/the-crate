import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

from st_aggrid import AgGrid, GridOptionsBuilder, StAggridTheme
from libs.utils import Utils


# --- Configuration & Theme
st.set_page_config(page_title="Rating Stats", page_icon="📊", layout="wide")

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

# --- Data Loading -------------------------------------------
if "album_df" not in st.session_state:
    st.error("⚠️ Dataset non caricato. Torna alla home per inizializzare i dati.")
    st.stop()
df = st.session_state.album_df

# --- Main Title ----------------------------------------------
st.title("📊 Album Rating Stats")

# --- Release Year Filter -------------------------------------
years = sorted(df["Release Year"].dropna().unique(), reverse=True)
languages = sorted(df["Language"].dropna().unique(), reverse=True)
genres = sorted(df["unique_genre"].dropna().unique(), reverse=True)

col1, col2, col3 = st.columns(3)
with col1:
    year_filter = st.selectbox("🎚️ Filter by Release Year", ["All years"] + years)
with col2:
    language_filter = st.selectbox("Filter by Language", ["All languages"] + languages)
with col3:
    genre_filter = st.selectbox("Filter by Genre", ["All genres"] + genres)

df_filtered = df.copy()

if year_filter != "All years":
    df_filtered = df_filtered[df_filtered["Release Year"] == year_filter]
if language_filter != "All languages":
    df_filtered = df_filtered[df_filtered["Language"] == language_filter]
if genre_filter != "All genres":
    df_filtered = df_filtered[df_filtered["unique_genre"] == genre_filter]

# --- Summary Metrics -----------------------------------------
col1, col2, col3 = st.columns(3)
col1.metric("Album Rated", len(df_filtered))
col2.metric("Artist Rated", df_filtered["Artist"].nunique())
col3.metric("Genre Rated", len(set(df_filtered.explode("Genre")["Genre"])))

st.markdown("---")

# --- Genre Statitics Table -----------------------------------
st.subheader("🎼 Genre Statistics")

# Filtriamo solo le righe con un genere valido
genre_df = df_filtered[df_filtered["unique_genre"].notna()].copy()

# Raggruppiamo per unique_genre
genre_summary = []
for genre, group in genre_df.groupby("unique_genre"):
    
    # Ordina per Rating, Masterpiece Tracks, Good Tracks
    sort_group = ( group.sort_values(
            by=["Score", "Masterpiece Tracks"],
            ascending=[False, False]
        ))

    top_album = sort_group.iloc[0]
    worst_album = sort_group.iloc[-1]
    
    genre_summary.append({
        "Genre": genre,
        "Album Number": len(group),
        "Average Rating": round(group["Score"].mean(), 2),
        "Median Rating": round(group["Score"].median(), 2),
        "Top Album": f"{top_album['Name']} ({top_album['Score']}/100)",
        "Worst Album": f"{worst_album['Name']} ({worst_album['Score']}/100)",
        "Oldest Album": int(group["Release Year"].min())
    })

# Create a dataframe
genre_stats_df = pd.DataFrame(genre_summary).sort_values(by="Album Number", ascending=False)

# Group by genre and pivoting by Release Year
release_year_genre_pivot = (
    genre_df.groupby(["Release Year", "unique_genre"])["Name"]
    .nunique()
    .reset_index(name="Album Count")
    .pivot(index="Release Year", columns="unique_genre", values="Album Count")
    .fillna(0)
    .astype(int)
)

gb = GridOptionsBuilder.from_dataframe(genre_stats_df)
gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, editable=False)
gb.configure_selection(selection_mode="single", use_checkbox=False)
grid_options = gb.build()

AgGrid(genre_stats_df, gridOptions=grid_options, fit_columns_on_grid_load=True, height=400, theme="balham")

st.markdown("---")

# --- Album Count by Release Year -----------------------------------
st.subheader("🎼 Album Count by Release Year")

# Keep only the last 10 years (descending)
latest_years = sorted(release_year_genre_pivot.index)[-10:][::-1]
release_year_genre_pivot = release_year_genre_pivot.loc[latest_years]

# Get the last 5 years in descending order
pivot_data = release_year_genre_pivot.sort_index(ascending=False).head(10)

# Plot the heatmap
fig = px.imshow(
    pivot_data,
    labels=dict(x="Genre", y="Release Year", color="Albums Count"),
    x=pivot_data.columns,
    y=pivot_data.index,
    color_continuous_scale="Reds",
    aspect="auto",
    text_auto=True
)

# Apply your custom Plotly theme
fig = Utils.apply_plotly_theme(fig)

# Display in Streamlit
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")    

# --- Language Color Pue plot ---
st.subheader("💿 Album by Language")
# Count vinyls per color (exclude missing/null values if needed)
language_counts = (
    df_filtered["Language"]
    .dropna()
    .value_counts()
    .reset_index()
    .rename(columns={"Count": "Language", "count": "Count"})
)

color_map = {
    "English": "#98bad5",
    "French": "#FF746C",
    "Spanish": "#e7d0f5",
    "Italian": "#3CB371"
}

col_left, col_right = st.columns([2, 2])

with col_left:
    fig_color = px.pie(
        language_counts,
        names="Language",
        values="Count",
        color="Language",
        color_discrete_map=color_map,
        hole=0.3  # Optional: donut-style
    )

    fig_color.update_traces(textposition='inside', textinfo='percent+label+value', textfont_size=16)
    fig_color.update_layout(title="Language Distribution", height=500)

    # Apply your custom theme
    fig_color = Utils.apply_plotly_theme(fig_color)

    # Show in Streamlit
    st.plotly_chart(fig_color, use_container_width=True)

with col_right:
    # Pivot senza sostituire con "-"
    lang_genre_stats = (
        df_filtered[df_filtered["Language"].isin(["Italian", "English"])]
        .groupby(["unique_genre", "Language"])["Score"]
        .mean()
        .reset_index()
        .pivot(index="unique_genre", columns="Language", values="Score")
        .round(2)
        .reset_index()
        .rename(columns={"unique_genre": "Genre"})
    )

    # Melt e pivot per imshow
    heatmap_data = lang_genre_stats.melt(
        id_vars="Genre", 
        var_name="Language", 
        value_name="Avg Rating"
    )

    matrix = heatmap_data.pivot(index="Genre", columns="Language", values="Avg Rating")

    # Matrice di testo (valori o "-")
    text_matrix = matrix.copy()
    text_matrix = text_matrix.fillna("–")
    text_matrix = text_matrix.applymap(lambda v: f"{v:.2f}" if isinstance(v, (int, float, np.floating)) else v)

    # Heatmap
    fig_heatmap = px.imshow(
        matrix,
        labels=dict(x="Language", y="Genre", color="Average Rating"),
        color_continuous_scale="Blues",
        aspect="auto"
    )

    # Annotazioni con i valori
    fig_heatmap.update_traces(
        text=text_matrix.values,
        texttemplate="%{text}",
        textfont_size=14,
        hovertemplate="Genre=%{y}<br>Language=%{x}<br>Avg Rating=%{z}<extra></extra>"
    )

    # Rimuovo il titolo
    fig_heatmap.update_layout(
        title="Per Generi",
        xaxis_side="top",
        height=600
    )

    fig_heatmap = Utils.apply_plotly_theme(fig_heatmap)
    st.plotly_chart(fig_heatmap, use_container_width=True)


st.markdown("---") 

st.subheader("📋 Vote Distribution")

df_filtered["rating_bins"] = df_filtered["Score"].apply(lambda x: Utils.rating_bin(x))
df_filtered["rating_bin_order"] = df_filtered["Score"].apply(lambda x: Utils.rating_bin_order(x))
rating_stats = ( df_filtered
    .groupby(["rating_bins", "rating_bin_order"]).size().reset_index(name='counts')
    .sort_values(by="rating_bin_order", ascending=False)
)

# 📊 Bar + 📈 Line (combo chart)
fig_ratings = go.Figure()

fig_ratings.add_trace(go.Bar(
    x=rating_stats["rating_bins"],
    y=rating_stats["counts"],
    name="Album Count",
    text=rating_stats["counts"],
    textposition="outside",
    marker_color="steelblue",
    yaxis="y"
))

# 🎛️ Minimal layout: axes only
fig_ratings.update_layout(
    xaxis=dict(
        title="Rating Bin",
        tickangle=-45
    ),
    yaxis=dict(
        title="Album Count"
    ),
    legend=dict(
        x=0.85,
        y=1.15,
        bgcolor="rgba(0,0,0,0)",
        font=dict(size=14)
    ),
    height=500
)

# 🌌 Apply your dark theme
fig_ratings = Utils.apply_plotly_theme(fig_ratings)
st.plotly_chart(fig_ratings, use_container_width=True)

st.markdown("---")

# --- Top Genre Plot ------------------------------------
st.subheader("🌟 Most Rated Genres")

genre_counts = df_filtered.groupby("unique_genre").agg(
    count=("unique_genre", "size"),
    avg_rating=("Score", "mean")
).reset_index()

top_genres = genre_counts.nlargest(20, "count")

# 📊 Bar + 📈 Line (combo chart)
fig_genre = go.Figure()

fig_genre.add_trace(go.Bar(
    x=top_genres["unique_genre"],
    y=top_genres["count"],
    name="Album Count",
    text=top_genres["count"],
    textposition="outside",
    marker_color="sandybrown",
    yaxis="y"
))

fig_genre.add_trace(go.Scatter(
    x=top_genres["unique_genre"],
    y=top_genres["avg_rating"],
    name="Avg. Rating",
    mode="lines+markers",
    line=dict(color="firebrick", width=4),
    marker=dict(size=12),
    yaxis="y2"
))

# 🎛️ Minimal layout: axes only
fig_genre.update_layout(
    xaxis=dict(
        title="Genre",
        tickangle=-45
    ),
    yaxis=dict(
        title="Album Count"
    ),
    yaxis2=dict(
        title="Avg. Rating",
        overlaying="y",
        side="right"
    ),
    legend=dict(
        x=0.85,
        y=1.15,
        bgcolor="rgba(0,0,0,0)",
        font=dict(size=14)
    ),
    height=500
)

# 🌌 Apply your dark theme
fig_genre = Utils.apply_plotly_theme(fig_genre)
st.plotly_chart(fig_genre, use_container_width=True)

st.markdown("---")

# --- Top Artists Plot -----------------------------------------
st.subheader("🌟 Top Artist")
artist_stats = ( df_filtered
    .groupby("Artist")
        .agg(
            count=("Name", "count"),
            avg_rating=("Score", "mean")
        )
    .reset_index()
)

artist_stats = artist_stats[artist_stats["count"] >= 2]
top_artists = artist_stats.nlargest(20, "avg_rating")

fig_artist = px.bar(
    top_artists,
    x="avg_rating",
    y="Artist",
    orientation="h",
    color="avg_rating",
    color_continuous_scale="Blues",
    text=top_artists.apply(lambda row: f"{row['avg_rating']:.2f} ({row['count']} album)", axis=1),
    labels={"avg_rating": "Average Rating", "Artist": "Artist"}
)

fig_artist.update_traces(textposition='inside', insidetextanchor="middle", textfont=dict(size=14))
fig_artist.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
fig_artist = Utils.apply_plotly_theme(fig_artist)
st.plotly_chart(fig_artist, use_container_width=True)
