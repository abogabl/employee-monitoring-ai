"""
لوحة CLI لعرض ملخص الحضور اليومي.
مثال:
python attendance_dashboard.py --date today
"""
from __future__ import annotations

import argparse
import logging
from datetime import datetime, date

from src.attendance_system import AttendanceSystem

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("attendance_dashboard")


def parse_date(arg: str) -> date:
    if arg == "today":
        return date.today()
    return date.fromisoformat(arg)


def main() -> None:
    parser = argparse.ArgumentParser(description="لوحة حضور بسيطة")
    parser.add_argument("--date", default="today", help="today أو YYYY-MM-DD")
    args = parser.parse_args()

    d = parse_date(args.date)
    sys = AttendanceSystem()

    rows = sys.get_daily_attendance(d)
    present_now = [r for r in rows if r.get("check_out_time") is None]
    present_ids = sorted({r["employee_id"] for r in present_now})

    # المتأخرون
    late = sys.get_late_employees(d)

    # إجمالي الساعات اليوم
    totals = {eid: sys.calculate_work_hours(eid, d) for eid in sorted({r["employee_id"] for r in rows})}

    # الأكثر إنتاجية (يعتمد على ساعات العمل فقط هنا؛ الإدارة المتقدمة في AttendanceManager)
    top_emp = max(totals.items(), key=lambda x: x[1]) if totals else (None, 0)

    print("==== Attendance Dashboard ====")
    print(f"Date: {d}")
    print(f"Present now: {len(present_ids)} -> {present_ids}")
    print("Late employees:")
    for r in late:
        print(f" - {r['employee_id']} ({r['employee_name']}), first_in={r['first_check_in']}")
    print("Total work hours today:")
    for eid, hrs in totals.items():
        print(f" - {eid}: {hrs:.2f} h")
    if top_emp[0]:
        print(f"Top by hours: {top_emp[0]} => {top_emp[1]:.2f} h")


if __name__ == "__main__":
    main()
