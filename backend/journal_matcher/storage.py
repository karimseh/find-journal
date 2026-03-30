import sqlite3


def init_db(db_path: str) -> sqlite3.Connection:
    """Initialize the SQLite database and return a connection.
    Creates the journals table with all columns for DGRSDT + Scimago + OpenAlex data.
    """
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # rows behave like dicts

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS journals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number INTEGER,
            title TEXT NOT NULL,
            issn TEXT,
            eissn TEXT,
            publisher TEXT,
            sjr REAL,
            quartile TEXT,
            h_index INTEGER,
            categories TEXT,
            areas TEXT,
            citations_per_doc REAL,
            open_access BOOLEAN DEFAULT 0,
            open_access_diamond BOOLEAN DEFAULT 0,
            openalex_id TEXT,
            openalex_topics TEXT,
            title_keywords TEXT
        )
    """
    )

    # Indexes for common query patterns
    conn.execute("CREATE INDEX IF NOT EXISTS idx_issn ON journals(issn)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_eissn ON journals(eissn)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_quartile ON journals(quartile)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sjr ON journals(sjr)")

    conn.commit()
    return conn


def insert_journals(conn: sqlite3.Connection, journals: list[dict]):
    """Bulk insert enriched journal records."""
    conn.executemany(
        """
        INSERT INTO journals
            (number, title, issn, eissn, publisher,
             sjr, quartile, h_index, categories, areas,
             citations_per_doc, open_access, open_access_diamond,
             openalex_id, openalex_topics, title_keywords)
        VALUES
            (:number, :title, :issn, :eissn, :publisher,
             :sjr, :quartile, :h_index, :categories, :areas,
             :citations_per_doc, :open_access, :open_access_diamond,
             :openalex_id, :openalex_topics, :title_keywords)
    """,
        journals,
    )
    conn.commit()


def query_all_journals(conn: sqlite3.Connection) -> list[dict]:
    """Get all journals."""
    rows = conn.execute("SELECT * FROM journals").fetchall()
    return [dict(row) for row in rows]


def query_filtered_journals(
    conn: sqlite3.Connection,
    quartiles: list[str] | None = None,
    min_sjr: float | None = None,
) -> list[dict]:
    """Get journals with optional quartile and SJR filters."""
    query = "SELECT * FROM journals WHERE 1=1"
    params = []

    if quartiles:
        placeholders = ",".join("?" for _ in quartiles)
        query += f" AND quartile IN ({placeholders})"
        params.extend(quartiles)

    if min_sjr is not None:
        query += " AND sjr >= ?"
        params.append(min_sjr)

    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def search_by_title(conn: sqlite3.Connection, query_str: str, limit: int = 20) -> list[dict]:
    """Search journals by title substring (case-insensitive)."""
    rows = conn.execute(
        "SELECT * FROM journals WHERE title LIKE ? LIMIT ?",
        (f"%{query_str}%", limit),
    ).fetchall()
    return [dict(row) for row in rows]


def get_stats(conn: sqlite3.Connection) -> dict:
    """Get database statistics: totals, enrichment rate, quartile distribution, top publishers."""
    total = conn.execute("SELECT COUNT(*) FROM journals").fetchone()[0]
    enriched = conn.execute("SELECT COUNT(*) FROM journals WHERE quartile IS NOT NULL").fetchone()[
        0
    ]

    # Quartile distribution
    quartile_rows = conn.execute(
        "SELECT quartile, COUNT(*) as cnt FROM journals WHERE quartile IS NOT NULL GROUP BY quartile ORDER BY quartile"
    ).fetchall()
    quartile_distribution = {row["quartile"]: row["cnt"] for row in quartile_rows}

    # Top 10 publishers
    publisher_rows = conn.execute(
        "SELECT publisher, COUNT(*) as cnt FROM journals WHERE publisher IS NOT NULL GROUP BY publisher ORDER BY cnt DESC LIMIT 10"
    ).fetchall()
    top_publishers = [
        {"publisher": row["publisher"], "count": row["cnt"]} for row in publisher_rows
    ]

    return {
        "total": total,
        "enriched": enriched,
        "enrichment_rate": round(enriched / total * 100, 1) if total > 0 else 0,
        "quartile_distribution": quartile_distribution,
        "top_publishers": top_publishers,
    }
