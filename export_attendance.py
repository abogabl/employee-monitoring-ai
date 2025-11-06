"""
تصدير تقارير الحضور إلى CSV/Excel.
مثال:
python export_attendance.py --start 2024-01-01 --end 2024-01-31 --format excel --output reports/attendance_jan2024.xlsx
"""
from __future__ import annotations

import argparse
import logging
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from src.attendance_system import AttendanceSystem

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("export_attendance")


def parse_date(s: str) -> date:
    return date.fromisoformat(s)


def main() -> None:
    parser = argparse.ArgumentParser(description="تصدير تقارير الحضور")
    parser.add_argument("--start", required=True, help="تاريخ البداية YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="تاريخ النهاية YYYY-MM-DD")
    parser.add_argument("--format", choices=["csv", "excel"], default="excel")
    parser.add_argument("--output", required=True, help="مسار ملف الإخراج")
    args = parser.parse_args()

    start = parse_date(args.start)
    end = parse_date(args.end)

    sys = AttendanceSystem()

    # جمع السجلات عبر المدى
    all_rows = []
    d = start
    while d <= end:
        rows = sys.get_daily_attendance(d)
        all_rows.extend(rows)
        d = date.fromordinal(d.toordinal() + 1)

    if not all_rows:
        logger.warning("لا توجد سجلات ضمن النطاق")
        return

    df = pd.DataFrame(all_rows)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.format == "csv":
        df.to_csv(out_path, index=False, encoding="utf-8-sig")
    else:
        try:
            df.to_excel(out_path, index=False)
        except Exception as e:
            logger.warning("فشل التصدير إلى Excel، سيتم التصدير CSV بدلاً من ذلك: %s", e)
            df.to_csv(out_path.with_suffix(".csv"), index=False, encoding="utf-8-sig")

    logger.info("تم حفظ التقرير إلى: %s", out_path)


if __name__ == "__main__":
    main()
