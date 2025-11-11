"""
سكريبت تجربة للكشف والتتبع باستخدام YOLOv8 + PersonTracker.
- يقرأ فيديو من المسار المُدخل أو من config.json (videos/sample.mp4)
- يرسم الصناديق ومعرّفات التتبع ويعرض FPS
- يحفظ فيديو ناتج باسم output_test.mp4 داخل مجلد videos/
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from src.detection_tracking import PersonDetector, PersonTracker
from src.utils import draw_text_with_background

# إعداد اللوجينغ
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("test_detection")


def load_default_video_path(config_path: Path) -> Optional[Path]:
    """قراءة مسار فيديو افتراضي من config.json إذا وُجد."""
    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        for cam in cfg.get("cameras", []):
            if isinstance(cam.get("source"), str) and cam["source"].endswith((".mp4", ".avi", ".mov")):
                return (config_path.parent / cam["source"]).resolve()
    except Exception as e:
        logger.warning("تعذر قراءة config.json: %s", e)
    return None


def main(video_path: Optional[str] = None) -> None:
    root = Path(__file__).parent.resolve()
    project_root = root
    config_path = project_root / "config.json"

    # اختيار الفيديو
    if video_path is None:
        default_path = load_default_video_path(config_path) if config_path.exists() else None
        if default_path and default_path.exists():
            video = str(default_path)
        else:
            video = str((project_root / "videos" / "sample.mp4").resolve())
            logger.info("سيتم محاولة فتح الفيديو الافتراضي: %s", video)
    else:
        video = video_path

    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        logger.error("تعذّر فتح الفيديو: %s", video)
        return

    # إعداد الكاشف والمتعقب
    detector = PersonDetector(model_size="n", device="cpu", conf=0.5, imgsz=640, half=False)
    tracker = PersonTracker(max_disappeared=30, max_distance=75)

    # إعداد كاتب الفيديو الناتج
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out_path = project_root / "videos" / "output_test.mp4"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (width, height))

    prev_time = time.time()
    frame_count = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # كشف
            detections = detector.detect(frame)

            # تحديث التتبع
            tracks = tracker.update(detections)

            # رسم صناديق الكشف
            vis = frame.copy()
            vis = detector.draw_boxes(vis, detections, color=(0, 255, 0))

            # رسم معرفات التتبع
            for tid, t in tracks.items():
                x1, y1, x2, y2 = t["box"]
                cv2.rectangle(vis, (x1, y1), (x2, y2), (255, 0, 0), 2)
                draw_text_with_background(vis, f"ID {tid}", (x1, max(15, y1 - 5)), color=(255, 255, 255))

            # حساب FPS
            frame_count += 1
            curr_time = time.time()
            dt = curr_time - prev_time
            if dt >= 1.0:
                fps_text = f"FPS: {frame_count / dt:.2f}"
                prev_time = curr_time
                frame_count = 0
            else:
                fps_text = None

            if fps_text:
                draw_text_with_background(vis, fps_text, (10, 25), color=(0, 255, 255))

            writer.write(vis)
            cv2.imshow("Detection & Tracking", vis)
            if cv2.waitKey(1) & 0xFF == 27:  # ESC
                break
    except KeyboardInterrupt:
        logger.info("تم الإيقاف بواسطة المستخدم.")
    except Exception as e:
        logger.exception("حدث خطأ أثناء المعالجة: %s", e)
    finally:
        cap.release()
        writer.release()
        cv2.destroyAllWindows()
        logger.info("تم حفظ الفيديو الناتج إلى: %s", out_path)


if __name__ == "__main__":
    main()
