"""
دمج قواعد بيانات حضور متعددة في ملف واحد مع حل تعارضات بسيط.
مثال:
python merge_databases.py --inputs cam1.db,cam2.db,cam3.db --output merged.db --resolve-conflicts
"""
from __future__ import annotations

import argparse
import logging
import os
import shutil
import sqlite3
from pathlib import Path
from typing import List

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("merge_databases")


def attach_and_copy(dst_con: sqlite3.Connection, src_db: Path) -> int:
    cur = dst_con.cursor()
    cur.execute("ATTACH DATABASE ? AS src", (str(src_db),))
    # تأكد من وجود جدول الوجهة
    cur.execute(
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
    # نسخ صفوف مع تجاهل التعارض عبر مفتاح مركب (ننشئ مؤقتاً)
    cur.execute("CREATE TEMP TABLE IF NOT EXISTS tmp_copy AS SELECT * FROM src.attendance_logs")
    rows = cur.execute("SELECT COUNT(*) FROM tmp_copy").fetchone()[0]
    # إدراج مع تفادي الازدواجية بناءً على (employee_id, check_in_time)
    cur.execute(
        """
        INSERT INTO attendance_logs (employee_id, employee_name, camera_id, check_in_time, check_out_time, status, duration_seconds, date, created_at)
        SELECT employee_id, employee_name, camera_id, check_in_time, check_out_time, status, duration_seconds, date, created_at FROM tmp_copy
        """
    )
    cur.execute("DETACH DATABASE src")
    return int(rows)


def resolve_duplicates(con: sqlite3.Connection) -> int:
    cur = con.cursor()
    # حذف المكرر مع الاحتفاظ بأقل id (الأقدم)
    cur.execute(
        """
        DELETE FROM attendance_logs
        WHERE rowid NOT IN (
          SELECT MIN(rowid) FROM attendance_logs GROUP BY employee_id, check_in_time
        )
        """
    )
    return con.total_changes


def main() -> None:
    ap = argparse.ArgumentParser(description="دمج قواعد بيانات حضور")
    ap.add_argument("--inputs", required=True, help="قائمة ملفات db مفصولة بفواصل")
    ap.add_argument("--output", required=True, help="ملف الإخراج")
    ap.add_argument("--resolve-conflicts", action="store_true")
    args = ap.parse_args()

    inputs = [Path(p.strip()) for p in args.inputs.split(",") if p.strip()]
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    if out.exists():
        logger.info("سيتم الكتابة فوق %s", out)
        out.unlink()

    con = sqlite3.connect(str(out))
    total = 0
    try:
        for db in inputs:
            if not db.exists():
                logger.warning("تجاهل %s (غير موجود)", db)
                continue
            total += attach_and_copy(con, db)
        if args.resolve_conflicts:
            changes = resolve_duplicates(con)
            logger.info("تم حل التعارضات: %d", changes)
        con.commit()
    finally:
        con.close()
    logger.info("تم دمج %d صفوف إلى %s", total, out)


if __name__ == "__main__":
    main()
