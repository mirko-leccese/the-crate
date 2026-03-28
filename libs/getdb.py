import html as _html


def _rich_text_to_html(segments):
    """Convert a Notion rich text array to a safe HTML string.

    Processes all segments (not just the first), preserving:
      - Newlines → <br>
      - Bold annotations → <strong>
      - Italic annotations → <em>
      - Code annotations → <code>

    Plain text content is HTML-escaped with html.escape() before any tags
    are added, so this output is safe to render with Jinja2's | safe filter.
    The only HTML in the result comes from our own controlled tag wrappers.
    """
    parts = []
    for seg in segments:
        # Use plain_text as fallback for non-text segment types (mentions, equations)
        if seg.get("type") != "text":
            parts.append(_html.escape(seg.get("plain_text", "")).replace("\n", "<br>"))
            continue

        content = seg["text"].get("content", "")
        # Escape user-supplied text before wrapping with our own HTML tags
        escaped = _html.escape(content).replace("\n", "<br>")

        ann = seg.get("annotations", {})
        if ann.get("code"):
            escaped = f"<code>{escaped}</code>"
        if ann.get("bold"):
            escaped = f"<strong>{escaped}</strong>"
        if ann.get("italic"):
            escaped = f"<em>{escaped}</em>"

        parts.append(escaped)

    return "".join(parts) or None


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
        "Duration": safe_get("Duration", "number"),
        "Notes": _rich_text_to_html(safe_get("Summary", "rich_text") or []),
        "Best Track": safe_get("Best Track", "rich_text")[0]["text"]["content"] if safe_get("Best Track", "rich_text") else None,
        "Picname": safe_get("Picname", "rich_text")[0]["text"]["content"] if safe_get("Picname", "rich_text") else None,
        "Release Date": safe_get("Release Date", "date", "start"),
        "Masterpiece Track Titles": safe_get("Masterpiece Track Titles", "rich_text")[0]["text"]["content"] if safe_get("Masterpiece Track Titles", "rich_text") else None,
        "Energy": safe_get("Energy", "number"),
        "Emotional Weight": safe_get("Emotional Weight", "number"),
        "Density": safe_get("Density", "number"),
        "Temperature": safe_get("Temperature", "number"),
        "Vastness": safe_get("Vastness", "number"),
    }
