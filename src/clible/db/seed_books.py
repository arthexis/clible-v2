# clible/db/seed_books.py
import json
import sqlite3
from pathlib import Path


def seed_books_if_empty(conn: sqlite3.Connection):
    """Add missing reference books without changing existing rows or verse data."""
    cursor = conn.cursor()
    existing = {row[0] for row in cursor.execute("SELECT id FROM books")}

    json_path = Path(__file__).resolve().parent.parent / "data" / "bible_structure.json"
    data = json.loads(json_path.read_text(encoding="utf-8"))

    missing = [book for book in data["books"] if book["id"] not in existing]
    if not missing:
        return
    for book in missing:
        conn.execute(
            """
            INSERT OR IGNORE INTO books (id, name, testament, position, chapters)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                book["id"],
                book["name"],
                book["testament"],
                book["position"],
                book["chapters"],
            ),
        )
    conn.commit()
