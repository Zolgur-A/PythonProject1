from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS processed_articles (
    article_hash TEXT PRIMARY KEY,
    source_path TEXT NOT NULL,
    processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

INSERT_SQL = """
INSERT OR IGNORE INTO processed_articles (article_hash, source_path)
VALUES (?, ?)
"""

SELECT_SQL = "SELECT 1 FROM processed_articles WHERE article_hash = ?"


class ProcessingState:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(SCHEMA_SQL)

    def has_processed(self, article_text: str) -> bool:
        article_hash = calculate_article_hash(article_text)
        with self._connect() as connection:
            row = connection.execute(SELECT_SQL, (article_hash,)).fetchone()
        return row is not None

    def mark_processed(self, source_path: Path, article_text: str) -> None:
        article_hash = calculate_article_hash(article_text)
        with self._connect() as connection:
            connection.execute(INSERT_SQL, (article_hash, str(source_path)))

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._database_path)
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()


def calculate_article_hash(article_text: str) -> str:
    normalized_text = article_text.strip().encode("utf-8")
    return hashlib.sha256(normalized_text).hexdigest()
