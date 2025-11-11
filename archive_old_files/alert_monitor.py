"""
خدمة مراقبة التنبيهات:
- تشغّل فحوصات AlertSystem كل فترة حسب config/alerts_config.json
- تمنع التكرار عبر throttling المدمج
- تعمل في الخلفية حتى الإيقاف

تشغيل:
python alert_monitor.py --daemon
"""
from __future__ import annotations

import argparse
import logging
import time

from src.alert_system import AlertSystem

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("alert_monitor")


def main() -> None:
    parser = argparse.ArgumentParser(description="مراقبة التنبيهات")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--config", default="config/alerts_config.json")
    args = parser.parse_args()

    system = AlertSystem(config_path=args.config)
    if not system.enabled:
        logger.warning("نظام التنبيهات غير مفعل في الإعدادات.")
        return

    try:
        while True:
            start = time.time()
            system.run_checks_once()
            spent = time.time() - start
            wait = max(5, system.check_interval - spent)
            time.sleep(wait)
    except KeyboardInterrupt:
        logger.info("تم الإيقاف.")


if __name__ == "__main__":
    main()
