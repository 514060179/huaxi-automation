from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class RunStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                token_prefix TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                event_type TEXT NOT NULL,
                method TEXT,
                host TEXT,
                path TEXT,
                status_code INTEGER,
                request_payload TEXT,
                response_summary TEXT,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            );
            """
        )
        self.conn.commit()

    def create_session(self, session_id: str, token_prefix: str, now: str) -> None:
        self.conn.execute(
            """
            INSERT INTO sessions (session_id, token_prefix, state, created_at, updated_at)
            VALUES (?, ?, 'created', ?, ?)
            """,
            (session_id, token_prefix, now, now),
        )
        self.conn.commit()

    def update_session_state(self, session_id: str, state: str, now: str) -> None:
        self.conn.execute(
            """
            UPDATE sessions SET state = ?, updated_at = ? WHERE session_id = ?
            """,
            (state, now, session_id),
        )
        self.conn.commit()

    def record_event(
        self,
        *,
        session_id: str,
        occurred_at: str,
        event_type: str,
        method: str | None = None,
        host: str | None = None,
        path: str | None = None,
        status_code: int | None = None,
        request_payload: dict | None = None,
        response_summary: dict | None = None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO events (
                session_id, occurred_at, event_type, method, host, path,
                status_code, request_payload, response_summary
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                occurred_at,
                event_type,
                method,
                host,
                path,
                status_code,
                json.dumps(request_payload, ensure_ascii=False) if request_payload else None,
                json.dumps(response_summary, ensure_ascii=False) if response_summary else None,
            ),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
