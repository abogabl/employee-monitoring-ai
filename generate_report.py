"""
CLI لتوليد التقارير بأنواعها.
أمثلة:
python generate_report.py --type daily --date 2024-01-15
python generate_report.py --type employee --id EMP001 --start 2024-01-01 --end 2024-01-31
python generate_report.py --type comparative --date 2024-01-15 --employees EMP001,EMP002,EMP003
"""
from __future__ import annotations

import argparse
import logging
from datetime import date
from pathlib import Path

from src.reporting import ReportGenerator
from src.report_visualizer import ReportVisualizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("generate_report")


def main() -> None:
    parser = argparse.ArgumentParser(description="مولد تقارير")
    parser.add_argument("--type", required=True, choices=["daily", "employee", "comparative", "segments", "visual"], help="نوع التقرير")
    parser.add_argument("--date", help="تاريخ اليوم YYYY-MM-DD")
    parser.add_argument("--start", help="بداية الفترة YYYY-MM-DD")
    parser.add_argument("--end", help="نهاية الفترة YYYY-MM-DD")
    parser.add_argument("--id", help="معرّف الموظف لتقرير الموظف")
    parser.add_argument("--employees", help="قائمة موظفين مفصولة بفواصل")
    parser.add_argument("--out", default="reports/output.csv", help="مسار ملف الإخراج")
    args = parser.parse_args()

    gen = ReportGenerator()

    if args.type == "daily":
        if not args.date:
            parser.error("--date مطلوب للتقرير اليومي")
        out = gen.generate_daily_summary(args.date, args.out)
        logger.info("تم إنشاء تقرير يومي: %s", out)

    elif args.type == "employee":
        if not args.id or not args.start or not args.end:
            parser.error("--id و --start و --end مطلوبة")
        df = gen.generate_employee_report(args.id, args.start, args.end)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.suffix.lower() == ".csv":
            df.to_csv(out, index=False, encoding="utf-8-sig")
        else:
            try:
                df.to_excel(out, index=False)
            except Exception:
                df.to_csv(out.with_suffix(".csv"), index=False, encoding="utf-8-sig")
        logger.info("تم إنشاء تقرير موظف: %s", out)

    elif args.type == "comparative":
        if not args.date:
            parser.error("--date مطلوب للمقارنة")
        viz = ReportVisualizer()
        bar = viz.employee_comparison_bar(args.date)
        dash_data = {"bar": bar}
        out = viz.create_dashboard(dash_data, output_path=Path(args.out).with_suffix(".html"))
        logger.info("تم إنشاء تقرير المقارنة: %s", out)

    elif args.type == "segments":
        # يتوقع إدخال CSV جاهز للمقاطع، هنا مثال تجريبي
        parser.error("نوع 'segments' يتطلب تمرير بيانات مصدر خارجية.")

    elif args.type == "visual":
        viz = ReportVisualizer()
        out = gen.generate_visual_report({"title": "Demo Report", "items": ["Sample line 1", "Sample line 2"]}, Path(args.out).with_suffix(".html"))
        logger.info("تم إنشاء تقرير بصري: %s", out)


if __name__ == "__main__":
    main()
