"""
فحص سلامة قاعدة بيانات الحضور وإصلاحات اختيارية.
مثال:
python validate_database.py --db attendance.db --fix
"""
from __future__ import annotations

import argparse
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("validate_database")


def parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def check_no_duplicates(con: sqlite3.Connection) -> Tuple[bool, int]:
    cur = con.execute("SELECT employee_id, check_in_time, COUNT(*) c FROM attendance_logs GROUP BY employee_id, check_in_time HAVING c>1")
    dups = cur.fetchall()
    if not dups:
        return True, 0
    if dups:
        logger.warning("تم العثور على سجلات مكررة: %d", len(dups))
    return False, len(dups)


def fix_no_duplicates(con: sqlite3.Connection) -> int:
    # حذف مكرر مع الاحتفاظ بأحدث id
    cur = con.execute("""
        DELETE FROM attendance_logs
        WHERE rowid NOT IN (
          SELECT MIN(rowid) FROM attendance_logs GROUP BY employee_id, check_in_time
        )
    """)
    return con.total_changes


def check_negative_durations(con: sqlite3.Connection) -> Tuple[bool, int]:
    cur = con.execute("SELECT id, duration_seconds FROM attendance_logs WHERE duration_seconds < 0")
    rows = cur.fetchall()
    return (len(rows) == 0, len(rows))


def fix_negative_durations(con: sqlite3.Connection) -> int:
    cur = con.execute("UPDATE attendance_logs SET duration_seconds=ABS(duration_seconds) WHERE duration_seconds<0")
    return con.total_changes


def check_checkout_after_checkin(con: sqlite3.Connection) -> Tuple[bool, int]:
    cur = con.execute("SELECT id, check_in_time, check_out_time FROM attendance_logs WHERE check_out_time IS NOT NULL")
    bad = 0
    for r in cur.fetchall():
        cin = parse_iso(r[1])
        cout = parse_iso(r[2])
        if cin and cout and cout < cin:
            bad += 1
    return bad == 0, bad


def fix_checkout_after_checkin(con: sqlite3.Connection) -> int:
    # تبادل الأوقات عند الانعكاس
    cur = con.execute("SELECT id, check_in_time, check_out_time FROM attendance_logs WHERE check_out_time IS NOT NULL")
    changes = 0
    for r in cur.fetchall():
        id_, cin, cout = r
        a = parse_iso(cin)
        b = parse_iso(cout)
        if a and b and b < a:
            con.execute("UPDATE attendance_logs SET check_in_time=?, check_out_time=? WHERE id=?", (cout, cin, id_))
            changes += 1
    return changes


def check_overlaps(con: sqlite3.Connection) -> Tuple[bool, int]:
    # تداخل زمني لنفس الموظف
    cur = con.execute("SELECT DISTINCT employee_id FROM attendance_logs")
    bad = 0
    for (emp,) in cur.fetchall():
        rows = con.execute("SELECT check_in_time, check_out_time FROM attendance_logs WHERE employee_id=? ORDER BY check_in_time", (emp,)).fetchall()
        prev_end = None
        for r in rows:
            s = parse_iso(r[0])
            e = parse_iso(r[1])
            if prev_end and s and e and s < prev_end:
                bad += 1
            if e:
                prev_end = e
    return bad == 0, bad


def check_foreign_keys(con: sqlite3.Connection, employees_json: Path) -> Tuple[bool, int]:
    if not employees_json.exists():
        return True, 0
    try:
        data = json.loads(employees_json.read_text(encoding="utf-8"))
        valid = set(data.keys())
        rows = con.execute("SELECT DISTINCT employee_id FROM attendance_logs").fetchall()
        missing = [emp for (emp,) in rows if emp not in valid]
        return len(missing) == 0, len(missing)
    except Exception:
        return True, 0


def check_timestamps(con: sqlite3.Connection) -> Tuple[bool, int]:
    # تحقق من الصيغة فقط
    cur = con.execute("SELECT id, check_in_time, check_out_time FROM attendance_logs")
    bad = 0
    for r in cur.fetchall():
        if r[1] and not parse_iso(r[1]):
            bad += 1
        if r[2] and not parse_iso(r[2]):
            bad += 1
    return bad == 0, bad


def main() -> None:
    ap = argparse.ArgumentParser(description="فحص سلامة قاعدة بيانات الحضور")
    ap.add_argument("--db", required=True)
    ap.add_argument("--fix", action="store_true")
    args = ap.parse_args()

    db = Path(args.db)
    if not db.exists():
        logger.error("قاعدة البيانات غير موجودة: %s", db)
        return

    con = sqlite3.connect(str(db))

    checks = [
        ("duplicates", check_no_duplicates, fix_no_duplicates),
        ("negative_durations", check_negative_durations, fix_negative_durations),
        ("order", check_checkout_after_checkin, fix_checkout_after_checkin),
        ("overlaps", check_overlaps, None),
        ("foreign_keys", lambda c: check_foreign_keys(c, Path("employees_database/employees.json")), None),
        ("timestamps", check_timestamps, None),
    ]

    for name, check_fn, fix_fn in checks:
        ok, count = check_fn(con)
        logger.info("Check %s: %s (%d)", name, "OK" if ok else "FAIL", count)
        if not ok and args.fix and fix_fn:
            changes = fix_fn(con)
            con.commit()
            logger.info("Applied fix for %s: changes=%s", name, changes)

    con.close()


if __name__ == "__main__":
    main()
