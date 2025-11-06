"""
بناء Dataset من فيديوهات:
مثال:
python dataset_builder.py --source videos/ --output dataset/ --extract-frames 30
- استخراج إطارات كل N إطار
- كشف الأشخاص (YOLOv8) وتوليد Annotations بصيغة YOLO
- قص صور الأشخاص وتنظيمها
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
from tqdm import tqdm

from src.detection_tracking import PersonDetector

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("dataset_builder")


def yolo_box_format(img_w: int, img_h: int, box: Tuple[int, int, int, int]) -> Tuple[float, float, float, float]:
    x1, y1, x2, y2 = box
    bw = x2 - x1
    bh = y2 - y1
    cx = x1 + bw / 2
    cy = y1 + bh / 2
    return (cx / img_w, cy / img_h, bw / img_w, bh / img_h)


def process_video(video_path: Path, out_dir: Path, frame_step: int, detector: PersonDetector) -> int:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        logger.warning("تعذر فتح الفيديو: %s", video_path)
        return 0
    img_dir = out_dir / "images"
    lbl_dir = out_dir / "labels"
    crop_dir = out_dir / "crops"
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)
    crop_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    idx = 0
    pbar = tqdm(total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0), desc=f"{video_path.name}", unit="f")
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        fno = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
        if fno % frame_step != 0:
            pbar.update(1)
            continue
        h, w = frame.shape[:2]
        dets = detector.detect(frame)
        if len(dets) == 0:
            pbar.update(1)
            continue
        # حفظ الصورة
        img_name = f"{video_path.stem}_{idx:06d}.jpg"
        img_path = img_dir / img_name
        cv2.imwrite(str(img_path), frame)
        # حفظ الملصق
        lbl_path = lbl_dir / img_name.replace(".jpg", ".txt")
        with lbl_path.open("w", encoding="utf-8") as f:
            for d in dets:
                x, y, x2, y2 = d["box"]
                # قص الشخص
                crop = frame[max(0, y):max(0, y2), max(0, x):max(0, x2)]
                if crop.size > 0:
                    cv2.imwrite(str(crop_dir / f"{video_path.stem}_{idx:06d}_{count}.jpg"), crop)
                cx, cy, bw, bh = yolo_box_format(w, h, (x, y, x2, y2))
                f.write(f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")
                count += 1
        idx += 1
        pbar.update(1)
    cap.release()
    pbar.close()
    return count


def main() -> None:
    ap = argparse.ArgumentParser(description="بناء Dataset من الفيديوهات")
    ap.add_argument("--source", required=True, help="مجلد الفيديوهات")
    ap.add_argument("--output", required=True, help="مجلد الإخراج")
    ap.add_argument("--extract-frames", type=int, default=30, help="استخراج كل N إطار")
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"], help="جهاز YOLO")
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--conf", type=float, default=0.5)
    args = ap.parse_args()

    src = Path(args.source)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    det = PersonDetector(model_size="n", device=args.device, conf=args.conf, imgsz=args.imgsz, half=(args.device=="cuda"))

    total = 0
    videos = [p for p in src.glob("**/*") if p.suffix.lower() in {".mp4", ".avi", ".mov", ".mkv"}]
    for v in videos:
        total += process_video(v, out, args.extract_frames, det)
    logger.info("تم إنشاء Dataset. إجمالي الكائنات: %d", total)


if __name__ == "__main__":
    main()
