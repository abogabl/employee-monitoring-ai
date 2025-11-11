"""
عرض سريع لآخر تقرير يومي موجود في reports/ مع ملخص.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd


def find_latest_daily_report(reports_dir: Path) -> Path | None:
    files = sorted(reports_dir.glob("daily_*.csv"), reverse=True)
    return files[0] if files else None


def main() -> None:
    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    f = find_latest_daily_report(reports_dir)
    if not f:
        print("لا يوجد تقرير يومي في reports/. قم بتشغيل النظام أولاً أو استخدم generate_report.py.")
        return
    df = pd.read_csv(f, encoding="utf-8-sig") if f.suffix == ".csv" else pd.read_excel(f)
    print(f"عرض تقرير: {f}")
    if df.empty:
        print("التقرير فارغ")
        return
    # ملخص بسيط
    total_employees = df["employee_id"].nunique() if "employee_id" in df.columns else len(df)
    total_seconds = int(df.get("duration_seconds", pd.Series()).sum()) if "duration_seconds" in df.columns else 0
    total_hours = total_seconds / 3600.0
    print(json.dumps({
        "total_employees": total_employees,
        "total_hours": round(total_hours, 2)
    }, ensure_ascii=False, indent=2))
    # عرض أول 10 صفوف
    print("\nأول 10 صفوف:\n")
    print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
