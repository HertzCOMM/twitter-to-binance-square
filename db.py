"""
SQLite state management:
- Track posted tweet IDs (deduplication)
- Save pagination cursor
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / 'state.db'


def _conn():
    con = sqlite3.connect(DB_PATH)
    con.execute('PRAGMA journal_mode=WAL')
    return con


def init_db():
    with _conn() as con:
        con.executescript('''
            CREATE TABLE IF NOT EXISTS posted_tweets (
                tweet_id TEXT PRIMARY KEY,
                posted_at TEXT DEFAULT (datetime('now')),
                square_post_id TEXT
            );
            CREATE TABLE IF NOT EXISTS sync_state (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
        ''')


def is_posted(tweet_id: str) -> bool:
    with _conn() as con:
        row = con.execute(
            'SELECT 1 FROM posted_tweets WHERE tweet_id = ?', (tweet_id,)
        ).fetchone()
    return row is not None


def mark_posted(tweet_id: str, square_post_id: str = ''):
    with _conn() as con:
        con.execute(
            'INSERT OR IGNORE INTO posted_tweets (tweet_id, square_post_id) VALUES (?, ?)',
            (tweet_id, square_post_id),
        )


def get_cursor() -> Optional[str]:
    with _conn() as con:
        row = con.execute(
            "SELECT value FROM sync_state WHERE key = 'cursor'",
        ).fetchone()
    return row[0] if row else None


def save_cursor(cursor: str):
    with _conn() as con:
        con.execute(
            "INSERT OR REPLACE INTO sync_state (key, value) VALUES ('cursor', ?)",
            (cursor,),
        )


def posted_count_today() -> int:
    with _conn() as con:
        row = con.execute(
            "SELECT COUNT(*) FROM posted_tweets WHERE posted_at >= date('now')"
        ).fetchone()
    return row[0] if row else 0
