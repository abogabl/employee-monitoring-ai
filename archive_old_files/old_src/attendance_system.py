"""
نظام حضور وانصراف باستخدام SQLite مع دعم المناطق الزمنية ونسخ احتياطي ومؤشرات.
"""
from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


@dataclass
class AttendanceRecord:
    id: int
    employee_id: str
    employee_name: str
    camera_id: str
    check_in_time: Optional[str]
    check_out_time: Optional[str]
    status: str
    duration_seconds: Optional[int]
    date: str
    created_at: str


class AttendanceSystem:
    """نظام إدارة الحضور والانصراف بخواص:
    - SQLite للتخزين
    - نسخ احتياطي تلقائي يومي
    - مؤشرات لتحسين الاستعلام
    - تواريخ/أوقات مدركة للمنطقة الزمنية
    """

    def __init__(self, db_path: str | Path = "attendance_db/attendance.db", timezone: str = "Africa/Cairo") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.timezone = timezone
        self._connect()
        self._init_db()
        self._maybe_daily_backup()

    # --------------------- اتصال ومعاملات ---------------------
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

    # --------------------- تهيئة القاعدة ---------------------
    def _init_db(self) -> None:
        with self.tx():
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS attendance_logs (
                  id INTEGER PRIMARY KEY,
                  employee_id TEXT,
                  employee_name TEXT,
                  camera_id TEXT,
                  check_in_time TEXT,
                  check_out_time TEXT,
                  status TEXT,
                  duration_seconds INTEGER,
                  date TEXT,
                  created_at TEXT
                )
                """
            )
            # مؤشرات
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_att_emp_date ON attendance_logs (employee_id, date)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_att_status ON attendance_logs (status)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_att_date ON attendance_logs (date)")

    # --------------------- وقت ومنطقة ---------------------
    def _tz(self) -> Optional[ZoneInfo]:
        try:
            return ZoneInfo(self.timezone) if ZoneInfo else None
        except Exception:
            return None

    def _now_local(self) -> datetime:
        tz = self._tz()
        now = datetime.utcnow()
        if tz:
            return now.astimezone(tz)
        return now

    def _to_local(self, dt: datetime) -> datetime:
        tz = self._tz()
        if dt.tzinfo is None and tz:
            return dt.replace(tzinfo=tz)
        if tz:
            return dt.astimezone(tz)
        return dt

    def _iso(self, dt: datetime) -> str:
        # نخزن بتنسيق ISO8601 شاملاً المنطقة الزمنية إن وجدت
        return self._to_local(dt).isoformat()

    def _date_str(self, dt: datetime) -> str:
        d = self._to_local(dt).date()
        return d.isoformat()

    # --------------------- نسخ احتياطي ---------------------
    def _maybe_daily_backup(self) -> None:
        try:
            backups_dir = self.db_path.parent / "backups"
            backups_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.utcnow().strftime("%Y%m%d")
            marker = backups_dir / f".last_{stamp}"
            if marker.exists():
                return
            # إنشاء نسخة احتياطية للملف إن وُجد
            if self.db_path.exists() and self.db_path.stat().st_size > 0:
                backup_path = backups_dir / f"attendance_{stamp}.db"
                with open(self.db_path, "rb") as src, open(backup_path, "wb") as dst:
                    dst.write(src.read())
                logger.info("تم إنشاء نسخة احتياطية: %s", backup_path)
            marker.touch()
        except Exception as e:
            logger.warning("فشل النسخ الاحتياطي: %s", e)

    # --------------------- عمليات أساسية ---------------------
    def _get_open_session(self, employee_id: str) -> Optional[sqlite3.Row]:
        cur = self.conn.execute(
            "SELECT * FROM attendance_logs WHERE employee_id=? AND check_out_time IS NULL ORDER BY id DESC LIMIT 1",
            (employee_id,),
        )
        return cur.fetchone()

    def check_in(self, employee_id: str, camera_id: str, timestamp: datetime, employee_name: str | None = None) -> bool:
        ts = self._to_local(timestamp)
        date_s = self._date_str(ts)
        # إن كانت هناك جلسة مفتوحة، لا تُكرر الدخول
        open_row = self._get_open_session(employee_id)
        if open_row is not None:
            logger.info("الموظف %s لديه جلسة مفتوحة بالفعل", employee_id)
            return False
        name = employee_name or employee_id
        with self.tx():
            self.conn.execute(
                """
                INSERT INTO attendance_logs (employee_id, employee_name, camera_id, check_in_time, check_out_time, status, duration_seconds, date, created_at)
                VALUES (?, ?, ?, ?, NULL, 'checked_in', NULL, ?, ?)
                """,
                (employee_id, name, camera_id, self._iso(ts), date_s, self._iso(self._now_local())),
            )
        logger.info("تسجيل دخول: %s @ %s", employee_id, ts)
        return True

    def check_out(self, employee_id: str, camera_id: str, timestamp: datetime) -> bool:
        ts = self._to_local(timestamp)
        open_row = self._get_open_session(employee_id)
        if open_row is None:
            logger.info("لا توجد جلسة مفتوحة للموظف %s", employee_id)
            return False
        # حساب المدة
        try:
            cin = datetime.fromisoformat(open_row["check_in_time"])  # type: ignore[arg-type]
        except Exception:
            cin = ts
        duration = int(max(0, (ts - cin).total_seconds()))
        with self.tx():
            self.conn.execute(
                """
                UPDATE attendance_logs
                SET check_out_time=?, status='checked_out', duration_seconds=?
                WHERE id=?
                """,
                (self._iso(ts), duration, int(open_row["id"])),
            )
        logger.info("تسجيل خروج: %s | مدة %ds", employee_id, duration)
        return True

    def update_status(self, employee_id: str, status: str, timestamp: datetime) -> None:
        ts = self._to_local(timestamp)
        open_row = self._get_open_session(employee_id)
        if open_row is None:
            return
        with self.tx():
            self.conn.execute("UPDATE attendance_logs SET status=? WHERE id=?", (status, int(open_row["id"])))
        logger.debug("تحديث حالة %s -> %s @ %s", employee_id, status, ts)

    def get_current_status(self, employee_id: str) -> Dict[str, Any]:
        row = self._get_open_session(employee_id)
        if row is None:
            return {"present": False, "status": "checked_out"}
        return {"present": True, "status": row["status"], "check_in_time": row["check_in_time"], "camera_id": row["camera_id"]}

    def is_employee_present(self, employee_id: str) -> bool:
        return self._get_open_session(employee_id) is not None

    # --------------------- استعلامات ---------------------
    def _query(self, sql: str, params: Iterable[Any] = ()) -> List[Dict[str, Any]]:
        cur = self.conn.execute(sql, tuple(params))
        rows = cur.fetchall()
        return [dict(r) for r in rows]

    def get_daily_attendance(self, d: date | str) -> List[Dict[str, Any]]:
        date_s = d if isinstance(d, str) else d.isoformat()
        return self._query("SELECT * FROM attendance_logs WHERE date=? ORDER BY check_in_time ASC", (date_s,))

    def get_employee_attendance(self, employee_id: str, start_date: date | str, end_date: date | str) -> List[Dict[str, Any]]:
        s = start_date if isinstance(start_date, str) else start_date.isoformat()
        e = end_date if isinstance(end_date, str) else end_date.isoformat()
        return self._query(
            "SELECT * FROM attendance_logs WHERE employee_id=? AND date BETWEEN ? AND ? ORDER BY date ASC, check_in_time ASC",
            (employee_id, s, e),
        )

    def calculate_work_hours(self, employee_id: str, d: date | str) -> float:
        date_s = d if isinstance(d, str) else d.isoformat()
        rows = self._query("SELECT check_in_time, check_out_time FROM attendance_logs WHERE employee_id=? AND date=?", (employee_id, date_s))
        total = 0.0
        now = self._now_local()
        for r in rows:
            try:
                cin = datetime.fromisoformat(r["check_in_time"]) if r["check_in_time"] else None
                cout = datetime.fromisoformat(r["check_out_time"]) if r["check_out_time"] else None
            except Exception:
                cin, cout = None, None
            if cin is None:
                continue
            if cout is None:
                cout = now
            total += max(0.0, (cout - cin).total_seconds())
        return total / 3600.0

    def get_late_employees(self, d: date | str | None = None, expected_time: str = "09:00") -> List[Dict[str, Any]]:
        if d is None:
            d = self._now_local().date()
        date_s = d if isinstance(d, str) else d.isoformat()
        rows = self._query(
            "SELECT employee_id, employee_name, MIN(check_in_time) as first_in FROM attendance_logs WHERE date=? GROUP BY employee_id, employee_name",
            (date_s,),
        )
        tz = self._tz()
        late: List[Dict[str, Any]] = []
        for r in rows:
            try:
                first_in = datetime.fromisoformat(r["first_in"]) if r["first_in"] else None
                exp_hour, exp_min = [int(x) for x in expected_time.split(":")]
                expected_dt = datetime.fromisoformat(f"{date_s}T{exp_hour:02d}:{exp_min:02d}:00")
                if tz:
                    expected_dt = expected_dt.replace(tzinfo=tz)
                if first_in and first_in > expected_dt:
                    late.append({"employee_id": r["employee_id"], "employee_name": r["employee_name"], "first_check_in": r["first_in"]})
            except Exception:
                continue
        return late

    def generate_daily_report(self, d: date | str | None = None) -> pd.DataFrame:
        if d is None:
            d = self._now_local().date()
        rows = self.get_daily_attendance(d)
        df = pd.DataFrame(rows)
        # حساب مدة لكل سجل في حال لم تكن موجودة
        if not df.empty:
            def _dur(r):
                if r.get("duration_seconds"):
                    return r["duration_seconds"]
                try:
                    cin = datetime.fromisoformat(r["check_in_time"]) if r.get("check_in_time") else None
                    cout = datetime.fromisoformat(r["check_out_time"]) if r.get("check_out_time") else None
                    if cin is None:
                        return 0
                    if cout is None:
                        cout = self._now_local()
                    return int(max(0, (cout - cin).total_seconds()))
                except Exception:
                    return 0
            df["duration_seconds"] = df.apply(_dur, axis=1)
        return df

    # --------------------- أدوات ---------------------
    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass
