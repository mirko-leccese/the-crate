import streamlit as st

st.set_page_config(page_title="Perché?", page_icon="💬", layout="wide")

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

st.title("💬 Perché questa dashboard?")
st.markdown(
    """
    Questa dashboard raccoglie le mie recensioni di album musicali e le rende navigabili e condivisibili.

    L'obiettivo è semplice: tenere traccia di quello che ascolto, valutarlo in modo sistematico e — perché no — suggerire qualcosa di interessante a chi capita qui.

    Usa il menu laterale per navigare tra le sezioni:
    - 🏆 **Album Ratings** — la classifica completa degli album recensiti
    - 📋 **Lists** — selezioni tematiche e liste curate
    - 🔍 **Rating Search** — cerca un artista o un album
    - 🎲 **Random Generator** — lascia che il caso scelga per te
    - 📊 **Rating Stats** — statistiche e grafici sull'intera collezione

    ---

    ### 📊 Criteri di Valutazione

    Gli album sono valutati in base a diversi criteri: qualità delle produzioni, dei testi, coerenza del progetto e presenza di brani memorabili. Il voto finale è uno **Score** da 0 a 100.

    | **Fascia** | **Punteggio** | **Descrizione** |
    |:----------:|:-------------:|:----------------|
    | 1 | 100 – 95 | **Capolavoro, praticamente perfetto.** Ogni traccia è di altissimo livello, con produzioni raffinate e testi profondi o innovativi. L'ascolto è coerente, coinvolgente e ricco di momenti iconici. Progetto di riferimento assoluto per il genere. |
    | 2 | 94 – 90 | **Altissimo livello, quasi perfetto.** Poche sbavature, grande cura nei dettagli. Produzioni solide, spesso originali, e testi di spessore. Presenza probabile di singoli memorabili o tracce simbolo della carriera dell'artista. |
    | 3 | 89 – 85 | **Album ottimo.** Molti brani di grande qualità, struttura coerente e ispirata. Alcuni picchi eccellenti, magari affiancati da tracce meno incisive. Lavoro ben pensato, con buone scelte stilistiche. |
    | 4 | 84 – 75 | **Buon livello.** L'ascolto è piacevole e ricco di spunti interessanti, anche se non sempre omogeneo. Le produzioni sono spesso valide, i testi efficaci ma non sempre brillanti. |
    | 5 | 74 – 70 | **Album discreto.** Progetto con alcuni momenti riusciti, ma anche brani trascurabili o ripetitivi. Qualche idea interessante, ma l'esecuzione può risultare incerta o discontinua. |
    | 6 | 69 – 60 | **Sufficiente o poco più.** Qualche spunto positivo affiora, ma il progetto risulta debole sul piano dell'identità o della qualità media. Produzioni o testi spesso anonimi o scolastici. |
    | 7 | 59 – 50 | **Album insufficiente.** Scarso impatto complessivo, tracce dimenticabili e poche — se non nessuna — da salvare. Le produzioni sono piatte e i testi poco ispirati. |
    | 8 | < 50 | **Gravemente insufficiente.** Nessuna traccia rilevante, ascolto povero di contenuti e di idee. Progetto senza direzione artistica, privo di originalità o qualità tecnica. |
    """
)
