"""
notion_to_sqlite.py — One-time migration: Notion database → local SQLite file.

Usage:
    python notion_to_sqlite.py

Reads credentials from notion-keys.json (local dev) or environment variables
(NOTION_TOKEN, RATING_DATABASE_ID). Writes all albums to albums.db.
Re-running the script is safe: the table is replaced each time.
"""

import json
import os
import sqlite3
from pathlib import Path

import pandas as pd

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from libs.notion import NotionClient
from libs.getdb import extract_album_info

DB_PATH = "albums.db"
TABLE_NAME = "albums"


def main():
    print("Starting Notion → SQLite migration...")

    # Load credentials — same logic as the original app.py
    if Path("notion-keys.json").exists():
        with open("notion-keys.json") as f:
            keys = json.load(f)
        notion_token = keys["NOTION_TOKEN"]
        rating_db_id = keys["RATING_DATABASE_ID"]
    else:
        notion_token = os.environ["NOTION_TOKEN"]
        rating_db_id = os.environ["RATING_DATABASE_ID"]

    # Fetch all pages from Notion
    print("Fetching pages from Notion API...")
    client = NotionClient(NOTION_TOKEN=notion_token)
    pages = client.get_db_pages(DATABASE_ID=rating_db_id)
    print(f"  Fetched {len(pages)} rows from Notion.")

    # Build DataFrame using existing extraction logic
    albums_data = [extract_album_info(p) for p in pages]
    df = pd.DataFrame(albums_data)

    # SQLite cannot store Python lists — serialize Genre column to JSON strings
    df["Genre"] = df["Genre"].apply(
        lambda x: json.dumps(x) if isinstance(x, list) else json.dumps([])
    )

    # Write to SQLite — replace table so the script is safely re-runnable
    conn = sqlite3.connect(DB_PATH)
    df.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)
    conn.close()

    print(f"  Wrote {len(df)} rows to table '{TABLE_NAME}'.")
    print(f"  Columns exported: {list(df.columns)}")
    print(f"Migration complete. Database saved to: {Path(DB_PATH).resolve()}")


if __name__ == "__main__":
    main()
