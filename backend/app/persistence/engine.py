"""Persistence Engine — SQLite storage, snapshots, migrations, integrity checks."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

import aiosqlite

logger = logging.getLogger("chronos.persistence")

SCHEMA_VERSION = 1

MIGRATIONS = {
    1: """
    CREATE TABLE IF NOT EXISTS meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        created_at REAL NOT NULL,
        sim_time REAL NOT NULL,
        data TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS autosave (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        updated_at REAL NOT NULL,
        sim_time REAL NOT NULL,
        data TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS event_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timeline_id TEXT,
        event_id TEXT,
        event_type TEXT,
        simulation_time REAL,
        payload TEXT,
        created_at REAL
    );
    CREATE INDEX IF NOT EXISTS idx_event_log_tl ON event_log(timeline_id);
    CREATE INDEX IF NOT EXISTS idx_snapshots_created ON snapshots(created_at);
    """,
}


class PersistenceEngine:
    """Local SQLite persistence — no cloud dependencies."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        self._db = await aiosqlite.connect(str(self.db_path))
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA synchronous=NORMAL")
        await self.migrate()
        logger.info("Connected to %s", self.db_path)

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        if not self._db:
            raise RuntimeError("Database not connected")
        return self._db

    async def migrate(self) -> None:
        await self.db.execute(
            "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        await self.db.commit()
        cur = await self.db.execute(
            "SELECT value FROM meta WHERE key = 'schema_version'"
        )
        row = await cur.fetchone()
        current = int(row["value"]) if row else 0

        for version in sorted(MIGRATIONS.keys()):
            if version > current:
                await self.db.executescript(MIGRATIONS[version])
                await self.db.execute(
                    "INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', ?)",
                    (str(version),),
                )
                await self.db.commit()
                logger.info("Migrated schema to v%d", version)

    async def save_autosave(self, export: dict[str, Any]) -> None:
        data = json.dumps(export)
        await self.db.execute(
            """
            INSERT INTO autosave (id, updated_at, sim_time, data)
            VALUES (1, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                updated_at = excluded.updated_at,
                sim_time = excluded.sim_time,
                data = excluded.data
            """,
            (time.time(), export.get("sim_time", 0.0), data),
        )
        await self.db.commit()

    async def load_autosave(self) -> Optional[dict[str, Any]]:
        cur = await self.db.execute("SELECT data FROM autosave WHERE id = 1")
        row = await cur.fetchone()
        if not row:
            return None
        return json.loads(row["data"])

    async def create_snapshot(self, name: str, export: dict[str, Any]) -> int:
        cur = await self.db.execute(
            """
            INSERT INTO snapshots (name, created_at, sim_time, data)
            VALUES (?, ?, ?, ?)
            """,
            (name, time.time(), export.get("sim_time", 0.0), json.dumps(export)),
        )
        await self.db.commit()
        return cur.lastrowid or 0

    async def list_snapshots(self) -> list[dict[str, Any]]:
        cur = await self.db.execute(
            """
            SELECT id, name, created_at, sim_time
            FROM snapshots ORDER BY created_at DESC
            """
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def load_snapshot(self, snapshot_id: int) -> Optional[dict[str, Any]]:
        cur = await self.db.execute(
            "SELECT data FROM snapshots WHERE id = ?", (snapshot_id,)
        )
        row = await cur.fetchone()
        if not row:
            return None
        return json.loads(row["data"])

    async def delete_snapshot(self, snapshot_id: int) -> bool:
        cur = await self.db.execute(
            "DELETE FROM snapshots WHERE id = ?", (snapshot_id,)
        )
        await self.db.commit()
        return cur.rowcount > 0

    async def append_event_log(
        self,
        timeline_id: str,
        event_id: str,
        event_type: str,
        simulation_time: float,
        payload: dict,
    ) -> None:
        await self.db.execute(
            """
            INSERT INTO event_log
                (timeline_id, event_id, event_type, simulation_time, payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                timeline_id,
                event_id,
                event_type,
                simulation_time,
                json.dumps(payload),
                time.time(),
            ),
        )
        await self.db.commit()

    async def integrity_check(self) -> dict[str, Any]:
        cur = await self.db.execute("PRAGMA integrity_check")
        row = await cur.fetchone()
        ok = row[0] == "ok" if row else False
        cur2 = await self.db.execute("SELECT COUNT(*) AS n FROM snapshots")
        snap_count = (await cur2.fetchone())["n"]
        cur3 = await self.db.execute("SELECT COUNT(*) AS n FROM autosave")
        auto_count = (await cur3.fetchone())["n"]
        return {
            "ok": ok,
            "detail": row[0] if row else "unknown",
            "snapshots": snap_count,
            "has_autosave": auto_count > 0,
            "db_path": str(self.db_path),
            "schema_version": SCHEMA_VERSION,
        }
