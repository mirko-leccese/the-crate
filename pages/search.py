import streamlit as st 
import pandas as pd 

st.set_page_config(page_title="Rating Search", page_icon="🔍", layout="wide")

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

if "album_df" not in st.session_state:
    st.error("⚠️ Dataset non caricato. Torna alla home per inizializzare i dati.")
else:
    df = st.session_state.album_df

    st.title("🔍 Search Album")
    # --- Campo di ricerca custom con JS che sincronizza con Streamlit ---
    st.markdown(
    """
    <section class='filters-panel filters-panel--search'>
        <div class='filters-panel__header filters-panel__header--inline'>
            🔍 Search for Album Name or Artist
        </div>
    </section>
    """,
    unsafe_allow_html=True,
    )
    query = st.text_input(
        "",
        placeholder="Type an album or artist name…",
        key="search_query_input",
        label_visibility="collapsed",
    )



    if query:
        result = df[df["Name"].str.contains(query, case=False) | df["Artist"].str.contains(query, case=False)]
        result = result.sort_values(by="Release Year", ascending=False)
        for i, row in result.iterrows():
            cols = st.columns([1.2, 4], gap="small")

            with cols[0]:
                if row["final_cover"]:
                    st.image(row["final_cover"])
                else:
                    st.text("No Cover")

            with cols[1]:
                st.markdown(f"<div style='font-size: 22px; font-weight: bold;'>{row['Name']} ({row['Release Year']})</div>", unsafe_allow_html=True)
                st.markdown(f"**Artist:** {row['Artist']}")

                # 🎵 Generi come tag
                if row["Genre"]:
                    tags_html = "".join([f"<span class='genre-tag'>{genre}</span>" for genre in row["Genre"]])
                    st.markdown(tags_html, unsafe_allow_html=True)

                st.markdown(f"{row['Notes']}")

                st.markdown(f"*Best Track*: {row['Best Track']}")

                rating_chip = f"""
                <div class="rating-chip">
                    <span class="rating-chip__icon">⭐</span>
                    <span class="rating-chip__value">{row["Score"]}/100</span>
                    <span class="rating-chip__meta">Tier {row['Tier']}° · Rank {row['Rank']}°</span>
                </div>
                """
                st.markdown(rating_chip, unsafe_allow_html=True)
            st.markdown('<div class="soft-divider"></div>', unsafe_allow_html=True)
            
