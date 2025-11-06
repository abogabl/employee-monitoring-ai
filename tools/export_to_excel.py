"""
تصدير محسّن إلى Excel مع أوراق متعددة ورسوم بيانية.
مثال:
python export_to_excel.py --db attendance.db --start 2024-01-01 --end 2024-01-31 --output reports/january.xlsx --with-charts
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import pandas as pd

from src.attendance_system import AttendanceSystem


def parse_date(s: str) -> date:
    return date.fromisoformat(s)


def main() -> None:
    ap = argparse.ArgumentParser(description="تصدير إلى Excel")
    ap.add_argument("--db", default="attendance_db/attendance.db")
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--with-charts", action="store_true")
    args = ap.parse_args()

    sys = AttendanceSystem(db_path=args.db)

    s = parse_date(args.start)
    e = parse_date(args.end)

    # تجميع السجلات
    rows = []
    d = s
    while d <= e:
        rows.extend(sys.get_daily_attendance(d))
        d = date.fromordinal(d.toordinal() + 1)
    df = pd.DataFrame(rows)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
        # تفاصيل
        if not df.empty:
            df.to_excel(writer, sheet_name="Details", index=False)
        else:
            pd.DataFrame([{"info": "No data"}]).to_excel(writer, sheet_name="Details", index=False)

        # ملخص ساعات لكل موظف
        if not df.empty:
            # حساب المدة إن لم تكن متوفرة
            if "duration_seconds" not in df.columns or df["duration_seconds"].isna().any():
                from datetime import datetime
                def _dur(r):
                    try:
                        cin = pd.to_datetime(r.get("check_in_time")) if r.get("check_in_time") else None
                        cout = pd.to_datetime(r.get("check_out_time")) if r.get("check_out_time") else None
                        if cin is None:
                            return 0
                        if cout is None:
                            cout = pd.Timestamp.now()
                        return int(max(0, (cout - cin).total_seconds()))
                    except Exception:
                        return 0
                df["duration_seconds"] = df.apply(_dur, axis=1)
            summary = df.groupby("employee_id")["duration_seconds"].sum().reset_index()
            summary["hours"] = summary["duration_seconds"] / 3600.0
            summary.to_excel(writer, sheet_name="Summary", index=False)

            # ورقة إحصاءات بسيطة
            stats = pd.DataFrame({
                "metric": ["total_employees", "total_hours"],
                "value": [summary.shape[0], summary["hours"].sum()],
            })
            stats.to_excel(writer, sheet_name="Statistics", index=False)

            if args.with_charts:
                wb = writer.book
                ws = writer.sheets["Summary"]
                chart = wb.add_chart({"type": "column"})
                # نطاقات: الأعمدة تبدأ من صفر
                # A2:A{n} للأسماء، C2:C{n} للساعات
                n = len(summary) + 1
                chart.add_series({
                    "name": "Hours",
                    "categories": ["Summary", 1, 0, n - 1, 0],
                    "values": ["Summary", 1, 2, n - 1, 2],
                })
                chart.set_title({"name": "Work Hours per Employee"})
                chart.set_x_axis({"name": "Employee"})
                chart.set_y_axis({"name": "Hours"})
                ws.insert_chart("E2", chart, {"x_scale": 1.2, "y_scale": 1.2})

    print(f"Excel saved to {out}")


if __name__ == "__main__":
    main()
