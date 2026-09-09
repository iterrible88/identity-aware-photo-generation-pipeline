from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import closing
from pathlib import Path


class Repository:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as db, db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY, purpose TEXT NOT NULL,
                    consent_confirmed INTEGER NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS references_ (
                    id TEXT PRIMARY KEY, session_id TEXT NOT NULL, path TEXT NOT NULL,
                    width INTEGER NOT NULL, height INTEGER NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                );
                CREATE TABLE IF NOT EXISTS generations (
                    id TEXT PRIMARY KEY, session_id TEXT NOT NULL, status TEXT NOT NULL,
                    prompt TEXT NOT NULL, idempotency_key TEXT NOT NULL,
                    provider_task_id TEXT, result_path TEXT, error TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(session_id, idempotency_key)
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, generation_id TEXT NOT NULL,
                    status TEXT NOT NULL, detail TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def execute(self, sql: str, values: tuple = ()) -> None:
        with self._lock, closing(self._connect()) as db, db:
            db.execute(sql, values)

    def one(self, sql: str, values: tuple = ()) -> dict | None:
        with closing(self._connect()) as db:
            row = db.execute(sql, values).fetchone()
            return dict(row) if row else None

    def all(self, sql: str, values: tuple = ()) -> list[dict]:
        with closing(self._connect()) as db:
            return [dict(row) for row in db.execute(sql, values).fetchall()]

    def update_generation(self, generation_id: str, status: str, **fields: str | None) -> None:
        allowed = {"provider_task_id", "result_path", "error"}
        assignments = ["status = ?"]
        values: list[str | None] = [status]
        for name, value in fields.items():
            if name not in allowed:
                raise ValueError(f"Unsupported field: {name}")
            assignments.append(f"{name} = ?")
            values.append(value)
        values.append(generation_id)
        self.execute(f"UPDATE generations SET {', '.join(assignments)} WHERE id = ?", tuple(values))
        self.execute(
            "INSERT INTO events(generation_id, status, detail) VALUES (?, ?, ?)",
            (generation_id, status, json.dumps(fields)),
        )
