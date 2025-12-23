"""
Alert history storage using SQLite.
- save alerts with type, message, priority, timestamp
- acknowledgment support
- simple queries
"""
from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


DB_DIR = Path("logs")
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "alerts_history.db"


@dataclass
class AlertRecord:
    id: int
    alert_type: str
    message: str
    priority: str
    timestamp: str
    acknowledged: int
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[str]


class AlertHistory:
    def __init__(self, db_path: str | Path = DB_PATH) -> None:
        self.db_path = Path(db_path)
        self._connect()
        self._init_db()

    def _connect(self) -> None:
        self.conn = sqlite3.connect(str(self.db_path), detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    @contextmanager
    def tx(self):
        try:
            yield
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def _init_db(self) -> None:
        with self.tx():
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts_history (
                  id INTEGER PRIMARY KEY,
                  alert_type TEXT,
                  message TEXT,
                  priority TEXT,
                  timestamp TEXT,
                  acknowledged INTEGER DEFAULT 0,
                  acknowledged_by TEXT,
                  acknowledged_at TEXT
                )
                """
            )
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_type_time ON alerts_history (alert_type, timestamp)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_ack ON alerts_history (acknowledged)")

    def add_alert(self, alert_type: str, message: str, priority: str) -> int:
        now = datetime.utcnow().isoformat()
        with self.tx():
            cur = self.conn.execute(
                "INSERT INTO alerts_history (alert_type, message, priority, timestamp, acknowledged) VALUES (?, ?, ?, ?, 0)",
                (alert_type, message, priority, now),
            )
            return int(cur.lastrowid)

    def acknowledge(self, alert_id: int, by: str) -> None:
        ts = datetime.utcnow().isoformat()
        with self.tx():
            self.conn.execute(
                "UPDATE alerts_history SET acknowledged=1, acknowledged_by=?, acknowledged_at=? WHERE id=?",
                (by, ts, alert_id),
            )

    def list_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM alerts_history ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]

    def get_unacknowledged(self, limit: int = 100) -> List[Dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM alerts_history WHERE acknowledged=0 ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]

    def query(self, where: str = "", params: Iterable[Any] = ()) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM alerts_history"
        if where:
            sql += " WHERE " + where
        sql += " ORDER BY id DESC"
        cur = self.conn.execute(sql, tuple(params))
        return [dict(r) for r in cur.fetchall()]

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass
