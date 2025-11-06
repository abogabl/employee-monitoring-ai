"""
إنشاء Dataset وجوه لموظف من فيديو:
مثال:
python face_dataset_creator.py --source video.mp4 --employee-id EMP001 --output-dir employees_database/faces/EMP001/
- استخراج وجوه بجودة جيدة مع تنوع زوايا/إضاءة قدر الإمكان
- Auto-labeling باسم الموظف
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import cv2
import numpy as np
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("face_dataset_creator")


def variance_of_laplacian(image: np.ndarray) -> float:
    return float(cv2.Laplacian(image, cv2.CV_64F).var())


def extract_faces_opencv(frame: np.ndarray) -> list[tuple[int, int, int, int]]:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = cascade.detectMultiScale(gray, 1.1, 5)
    res = []
    for (x, y, w, h) in faces:
        res.append((int(x), int(y), int(x + w), int(y + h)))
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description="بناء Dataset وجوه لموظف من فيديو")
    ap.add_argument("--source", required=True)
    ap.add_argument("--employee-id", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--max-images", type=int, default=100)
    args = ap.parse_args()

    src = Path(args.source)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(src))
    if not cap.isOpened():
        logger.error("تعذر فتح المصدر: %s", src)
        return

    saved = 0
    pbar = tqdm(total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0), desc=src.name, unit="f")
    idx = 0
    while saved < args.max_images:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % 3 != 0:  # تقليل الكثافة
            idx += 1
            pbar.update(1)
            continue
        boxes = extract_faces_opencv(frame)
        for (x1, y1, x2, y2) in boxes:
            crop = frame[max(0, y1):max(0, y2), max(0, x1):max(0, x2)]
            if crop.size == 0:
                continue
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            sharp = variance_of_laplacian(gray)
            if sharp < 60:  # تصفية الباهت
                continue
            out_path = out / f"{args.employee_id}_{saved:04d}.jpg"
            cv2.imwrite(str(out_path), crop)
            saved += 1
            if saved >= args.max_images:
                break
        idx += 1
        pbar.update(1)
    pbar.close()
    cap.release()
    logger.info("تم حفظ %d صورة لوجه الموظف %s في %s", saved, args.employee_id, out)


if __name__ == "__main__":
    main()
