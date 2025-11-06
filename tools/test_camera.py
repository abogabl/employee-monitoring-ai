"""
اختبار اتصال الكاميرا/المصدر وقياس FPS سريع.
مثال:
python test_camera.py --camera-id cam1
python test_camera.py --source rtsp://...
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import cv2

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("test_camera")


def load_source_from_config(camera_id: str, cfg_path: Path = Path("config/cameras_config.json")) -> str | None:
    if not cfg_path.exists():
        return None
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        for cam in data.get("cameras", []):
            if str(cam.get("id")) == camera_id:
                return str(cam.get("source"))
    except Exception:
        return None
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description="اختبار الكاميرا/المصدر")
    ap.add_argument("--camera-id", help="معرف كاميرا من config/cameras_config.json")
    ap.add_argument("--source", help="مصدر مباشر (رقم/rtsp/file)")
    ap.add_argument("--seconds", type=int, default=5)
    args = ap.parse_args()

    src = args.source
    if not src and args.camera_id:
        src = load_source_from_config(args.camera_id)
    if src is None:
        logger.error("يرجى تمرير --source أو --camera-id")
        return

    cap = cv2.VideoCapture(int(src) if src.isdigit() else src)
    if not cap.isOpened():
        logger.error("تعذر فتح المصدر: %s", src)
        return
    frames = 0
    t0 = time.time()
    while (time.time() - t0) < args.seconds:
        ok, _ = cap.read()
        if not ok:
            break
        frames += 1
    cap.release()
    dt = time.time() - t0
    fps = frames / dt if dt > 0 else 0.0
    logger.info("Frames=%d Time=%.2fs FPS=%.1f", frames, dt, fps)


if __name__ == "__main__":
    main()
