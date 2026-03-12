import streamlit as st
import json
import math

# Page configuration
st.set_page_config(page_title="Lists", page_icon="📋", layout="wide")

with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

with st.sidebar:
    st.page_link('main.py', label='Home', icon='🏠')
    st.page_link('pages/top_albums.py', label='Top Album', icon='🏆')
    st.page_link('pages/lists.py', label='Lists', icon="📋")
    st.page_link('pages/search.py', label='Search Ratings', icon='🔍')
    st.page_link('pages/random.py', label='Random Generator', icon='#️⃣')
    st.page_link('pages/stats.py', label='Rating Stats', icon='📊')
    st.page_link('pages/perche.py', label='Perché?', icon='💬')

# Check session state
if "album_df" not in st.session_state:
    st.error("⚠️ Dataset non caricato. Torna alla home per inizializzare i dati.")
    st.stop()

df = st.session_state.album_df

st.title("📋 Curated Lists")

# Load the themed album lists
try:
    with open("lists.json", "r", encoding="utf-8") as f:
        album_lists = json.load(f)
except FileNotFoundError:
    st.error("⚠️ File 'lists.json' non trovato.")
    st.stop()

# UI: Dropdown to select a list
list_names = list(album_lists.keys())
with st.container():
    st.markdown(
        "<section class='filters-panel filters-panel--compact'><div class='filters-panel__header filters-panel__header--inline'>🎯 Seleziona una lista a tema</div>",
        unsafe_allow_html=True,
    )
    selected_list = st.selectbox(
        "",
        options=[""] + list_names,
        label_visibility="collapsed",
    )
    st.markdown("</section>", unsafe_allow_html=True)

# Display albums if a list is selected
if selected_list:
    selected_albums = album_lists[selected_list]["list"]
    current_description = album_lists[selected_list]["description"]

    # Extract and match albums from the DataFrame
    matched_df = df[df.apply(lambda row: f"{row['Name']} - {row['Artist']}" in selected_albums, axis=1)]

    if matched_df.empty:
        st.warning("Nessun album trovato nel dataset per questa lista.")
    else:
        num_albums = len(matched_df)
        cols_per_row = 5
        num_rows = math.ceil(num_albums / cols_per_row)

        st.markdown(f"### 📜 {selected_list}")

        st.markdown(f"{current_description}")

        album_iter = matched_df.iterrows()
        for _ in range(num_rows):
            cols = st.columns(cols_per_row)
            for col in cols:
                try:
                    _, album = next(album_iter)
                    with col:
                        st.image(album["final_cover"], use_container_width=True)
                        st.markdown(f"**{album['Name']}** ({album['Release Year']})  \n*{album['Artist']}*", unsafe_allow_html=True)
                except StopIteration:
                    break
