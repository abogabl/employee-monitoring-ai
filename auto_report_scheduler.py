"""
جدولة تقارير تلقائية وإرسالها بالبريد.
مثال:
python auto_report_scheduler.py --schedule daily --time 18:00 --email manager@company.com
"""
from __future__ import annotations

import argparse
import logging
import time
from datetime import datetime, timedelta

from src.reporting import ReportGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("auto_report_scheduler")


def parse_time(t: str) -> timedelta:
    hh, mm = [int(x) for x in t.split(":")]
    return timedelta(hours=hh, minutes=mm)


def main() -> None:
    parser = argparse.ArgumentParser(description="جدولة تقارير تلقائية")
    parser.add_argument("--schedule", choices=["daily"], required=True)
    parser.add_argument("--time", required=True, help="HH:MM 24h")
    parser.add_argument("--email", required=False, default="", help="بريد المستلم للاستخدام مع SMTP مُعد مسبقاً")
    args = parser.parse_args()

    gen = ReportGenerator()

    target_td = parse_time(args.time)
    logger.info("سيتم إنشاء تقرير يومي عند %s كل يوم.", args.time)
    while True:
        now = datetime.now()
        target = now.replace(hour=target_td.seconds // 3600, minute=(target_td.seconds % 3600) // 60, second=0, microsecond=0)
        if target < now:
            target = target + timedelta(days=1)
        wait_s = (target - now).total_seconds()
        logger.info("الانتظار %.0f ثانية حتى %s", wait_s, target)
        time.sleep(max(1, min(wait_s, 3600)))  # نوم على دفعات بحد أقصى ساعة
        # تحقق مرة أخرى قبل التنفيذ
        now2 = datetime.now()
        if abs((now2 - target).total_seconds()) <= 60:
            out = gen.generate_daily_summary(now2.date().isoformat(), f"reports/daily_{now2.date().isoformat()}.csv")
            logger.info("تم إنشاء تقرير يومي: %s", out)
            if args.email:
                gen.send_email(args.email, subject=f"Daily Attendance Report {now2.date().isoformat()}", body="مرفق التقرير اليومي.", attachments=[out])


if __name__ == "__main__":
    main()
