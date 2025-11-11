"""
تجربة التعرف على الوجوه باستخدام InsightFace.
- يدعم صورة أو فيديو
- يرسم الأسماء واحتمالات التشابه
مثال:
python test_face_recognition.py --image path/to/img.jpg
python test_face_recognition.py --video path/to/video.mp4
"""
from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from src.face_recognition_system import FaceRecognitionSystem
from src.utils import draw_text_with_background

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("test_face_recognition")


def run_on_image(image_path: Path, frs: FaceRecognitionSystem) -> None:
    img = cv2.imdecode(np.fromfile(str(image_path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        logger.error("تعذّر قراءة الصورة: %s", image_path)
        return
    t0 = time.time()
    faces = frs.detect_faces(img)
    for f in faces:
        emp_id, sim, name = frs.recognize_face(f["embedding"])
        x1, y1, x2, y2 = f["box"]
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = name or "Unknown"
        draw_text_with_background(img, f"{label} ({sim:.2f})", (x1, max(15, y1 - 5)))
    dt = (time.time() - t0) * 1000
    logger.info("عدد الوجوه: %d | الزمن: %.1f ms", len(faces), dt)
    cv2.imshow("Face Recognition - Image", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def run_on_video(video_path: Path, frs: FaceRecognitionSystem) -> None:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        logger.error("تعذر فتح الفيديو: %s", video_path)
        return
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        faces = frs.detect_faces(frame)
        for f in faces:
            emp_id, sim, name = frs.recognize_face(f["embedding"])
            x1, y1, x2, y2 = f["box"]
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = name or "Unknown"
            draw_text_with_background(frame, f"{label} ({sim:.2f})", (x1, max(15, y1 - 5)))
        cv2.imshow("Face Recognition - Video", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break
    cap.release()
    cv2.destroyAllWindows()


def main() -> None:
    parser = argparse.ArgumentParser(description="اختبار التعرف على الوجوه")
    parser.add_argument("--image", type=str, help="مسار الصورة")
    parser.add_argument("--video", type=str, help="مسار الفيديو")
    parser.add_argument("--encodings", default="models/face_encodings.pkl", help="ملف التضمينات")
    parser.add_argument("--threshold", type=float, default=0.6, help="حد التشابه")
    args = parser.parse_args()

    frs = FaceRecognitionSystem(model_name="buffalo_l", threshold=args.threshold)
    frs.load_encodings(args.encodings)

    if args.image:
        run_on_image(Path(args.image), frs)
    elif args.video:
        run_on_video(Path(args.video), frs)
    else:
        logger.error("يرجى تمرير --image أو --video")


if __name__ == "__main__":
    main()
