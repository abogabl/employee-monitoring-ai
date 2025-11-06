"""
run_multi_camera.py
تشغيل عدة كاميرات وفق إعدادات config/cameras_config.json مع خيارات CLI.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.multi_camera_runner import MultiCameraRunner

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("run_multi_camera")


def main() -> None:
    parser = argparse.ArgumentParser(description="تشغيل عدة كاميرات")
    parser.add_argument("--cameras", default="", help="قائمة معرفات كاميرات مفصولة بفواصل لتشغيلها فقط")
    parser.add_argument("--config", default="config/cameras_config.json", help="مسار ملف إعداد الكاميرات")
    parser.add_argument("--with-dashboard", action="store_true", help="تشغيل لوحة مراقبة (غير مفعلة حالياً)")
    parser.add_argument("--test-mode", action="store_true", help="وضع الاختبار بفيديوهات مسجلة")
    parser.add_argument("--videos", default="", help="قائمة فيديوهات للاختبار cam1,cam2 بحسب الترتيب")
    args = parser.parse_args()

    runner = MultiCameraRunner(args.config)
    runner.load_config()

    only_ids = [s.strip() for s in args.cameras.split(",") if s.strip()] if args.cameras else None

    # وضع الاختبار: استبدل مصادر الكاميرات بالفيديوهات
    if args.test_mode and args.videos:
        vids = [s.strip() for s in args.videos.split(",") if s.strip()]
        cams = [c for c in runner.config.get("cameras", []) if c.get("enabled", True)]  # type: ignore[attr-defined]
        for i, cam in enumerate(cams):
            if i < len(vids):
                cam["source"] = vids[i]

    runner.start_all_cameras(only_ids=only_ids)
    try:
        runner.monitor_loop(interval=5.0)
    except KeyboardInterrupt:
        logger.info("إيقاف جميع الكاميرات...")
        runner.stop_all_cameras()


if __name__ == "__main__":
    main()
