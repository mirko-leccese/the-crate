# The Crate

> Un archivio personale di ascolti — perché ogni disco merita una seconda chance.

<!-- screenshot -->

---

## What is this?

The Crate is my personal music album review archive, built as a Flask web app and connected to a Notion database as its data source. It's not a music magazine, and it's not a definitive guide to the most important albums in history — it's simply a place where I keep track of what I listen to, rate it with a structured scoring system, and make it browsable and shareable. The idea was embarrassingly simple: I was already listening to a lot of music with a growing obsession for cataloguing things, so I built this. If you find something interesting while browsing, even better.

---

## Features

- **Home** — stat cards (total albums, artists, genres, average score), two carousels (new releases from the current year and archive picks), a top-5 all-time ranking table, and a click-to-expand album detail modal
- **Archivio** — full ranked album list with filters by genre, subgenre, language, cover color, year range, and minimum score
- **Cerca** — free-text search by album title or artist name
- **Random!** — pick random albums from the archive, with the same filters as Archivio (genre, language, color, year range, score)
- **Perché?** — an about page explaining the project, the scoring criteria, and the origin of the name
- **Scoring system** — each album gets a score from 0 to 100, derived from individual sub-scores for production and vocal/lyrical quality, with a tier system from 1 (masterpiece) to 8 (severely insufficient)
- **Album detail modal** — click any carousel cover on the home page to open a full album card in a modal overlay, with score details, genre tags, and notes
- **Cover images** — served from local static files when available, with fallback to external URLs

---

## Data source

All album data comes from a Notion database, fetched at app startup via the Notion API. Each record contains the album name, artist, release date, genre tags, scores, notes, cover image reference, and other metadata. Album cover images are stored locally in `static/artworks/` when available; otherwise the app falls back to external cover URLs stored in the database. The data is loaded once at startup and held in memory for the lifetime of the process.

---

## Tech stack

- **Python / Flask** — web framework and routing
- **Notion API** — data source (custom client in `libs/notion.py`)
- **Pandas** — data loading, filtering, and aggregation
- **Jinja2** — server-side HTML templating
- **Vanilla HTML / CSS / JS** — no frontend framework; all UI is hand-written
- **Gunicorn** — production WSGI server
- **Deployment** — `render.yaml` included for one-click deploy on [Render](https://render.com)

---

## Getting started

**1. Clone the repo**

```bash
git clone https://github.com/your-username/the-crate.git
cd the-crate
```

**2. Create and activate a virtual environment**

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Set up environment variables**

The app can read credentials from a local `notion-keys.json` file (for development) or from environment variables (for production).

To use environment variables, create a `.env` file in the project root:

```
NOTION_TOKEN=your_notion_integration_token
RATING_DATABASE_ID=your_notion_database_id
```

Alternatively, create `notion-keys.json` in the project root:

```json
{
  "NOTION_TOKEN": "your_notion_integration_token",
  "RATING_DATABASE_ID": "your_notion_database_id"
}
```

**5. Run the app**

```bash
flask run
```

Or directly:

```bash
python app.py
```

> **Note:** On macOS Monterey and later, port 5000 may be occupied by AirPlay Receiver. Either disable it in System Settings → General → AirDrop & Handoff, or run on a different port: `flask run --port 5001`

---

## Environment variables

| Variable | Description | Required |
|---|---|---|
| `NOTION_TOKEN` | Notion integration token with read access to the database | Yes |
| `RATING_DATABASE_ID` | ID of the Notion database containing the album reviews | Yes |

---

## Project structure

```
the-crate/
├── app.py                  # Flask app, routes, data loading
├── requirements.txt
├── render.yaml             # Render deployment config
├── notion-keys.json        # Local dev credentials (not committed)
├── libs/
│   ├── notion.py           # Notion API client
│   ├── getdb.py            # Album data extraction
│   └── utils.py            # Genre mapping and helpers
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── top_albums.html
│   ├── search.html
│   ├── random.html
│   ├── perche.html
│   └── partials/
│       └── album_card.html
└── static/
    ├── style.css
    ├── crate-page.png
    └── artworks/           # Local album cover images
```

---

## Nota personale

Questo progetto nasce da una combinazione di due ossessioni: la musica e l'organizzazione. Ho iniziato ad ascoltare con più attenzione, ho iniziato a prendere appunti, e a un certo punto mi è sembrato naturale costruire qualcosa per raccogliere tutto in modo ordinato. Non è un prodotto, non è una startup, non è nemmeno un blog — è semplicemente il mio crate digitale. Se ti capita di trovare un disco che non conoscevi, sono contento. Se pensi che i miei voti siano discutibili, hai probabilmente ragione.
