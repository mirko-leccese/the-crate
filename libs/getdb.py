

# Simula il caricamento dal database Notion
def extract_album_info(page):
    props = page["properties"]

    def safe_get(*keys, default=None):
        current = props
        for key in keys:
            current = current.get(key, {}) if current is not None else {}
        return current if current != {} else default

    # Safe access to the cover URL
    cover_url = None
    if page.get("cover") and page["cover"].get("external"):
        cover_url = page["cover"]["external"].get("url")

    # Genres
    genres = [genre["name"] for genre in page["properties"]["Genre"]["multi_select"]]

    return {
        "Created": page.get("created_time"),
        "Name": safe_get("Name", "title")[0]["text"]["content"] if safe_get("Name", "title") else None,
        "Artist": safe_get("Artist", "select", "name"),
        "Release Year": safe_get("Release Year", "formula", "number"),
        "Special": safe_get("Special", "checkbox"),
        "Published": safe_get("Published", "checkbox"),
        "Total Tracks": safe_get("Total Tracks", "number"),
        "Overall": safe_get("Overall", "number"),
        "Production": safe_get("Production", "number"),
        "Lyrics/Novelty": safe_get("Lyrics/Novelty", "number"),
        "Score": safe_get("Score", "formula", "number"),
        "Masterpiece Tracks": safe_get("Masterpiece Tracks", "number"),
        "Cover": cover_url,
        "Language": safe_get("Language", "select", "name"),
        "Genre": genres,
        "Color": safe_get("Color", "select", "name"),
        "Notes": safe_get("Summary", "rich_text")[0]["text"]["content"] if safe_get("Summary", "rich_text") else None,
        "Best Track": safe_get("Best Track", "rich_text")[0]["text"]["content"] if safe_get("Summary", "rich_text") else None,
        "Picname": safe_get("Picname", "rich_text")[0]["text"]["content"] if safe_get("Picname", "rich_text") else None,
        "Release Date": safe_get("Release Date", "date", "start"),
        "Masterpiece Track Titles": safe_get("Masterpiece Track Titles", "rich_text")[0]["text"]["content"] if safe_get("Masterpiece Track Titles", "rich_text") else None
    }

