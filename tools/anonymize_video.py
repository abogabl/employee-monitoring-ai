"""
إخفاء الهويات في الفيديو:
مثال:
python anonymize_video.py --input video.mp4 --output anonymized.mp4 --method blur
طرق: blur (Gaussian)، pixelate، mask (مربع أسود)
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import cv2

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("anonymize_video")


def anonymize_frame(frame, faces, method: str = "blur"):
    out = frame.copy()
    for (x, y, w, h) in faces:
        if method == "pixelate":
            roi = out[y:y+h, x:x+w]
            if roi.size == 0:
                continue
            small = cv2.resize(roi, (max(1, w // 12), max(1, h // 12)), interpolation=cv2.INTER_LINEAR)
            pix = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
            out[y:y+h, x:x+w] = pix
        elif method == "mask":
            cv2.rectangle(out, (x, y), (x+w, y+h), (0, 0, 0), -1)
        else:  # blur
            roi = out[y:y+h, x:x+w]
            if roi.size == 0:
                continue
            k = max(11, (min(w, h) // 5) | 1)
            roi = cv2.GaussianBlur(roi, (k, k), 0)
            out[y:y+h, x:x+w] = roi
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="إخفاء الهوية في الفيديو")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--method", choices=["blur", "pixelate", "mask"], default="blur")
    args = ap.parse_args()

    src = Path(args.input)
    dst = Path(args.output)
    dst.parent.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(src))
    if not cap.isOpened():
        logger.error("تعذر فتح الفيديو: %s", src)
        return
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    writer = cv2.VideoWriter(str(dst), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(gray, 1.1, 5)
            out = anonymize_frame(frame, faces, method=args.method)
            writer.write(out)
    finally:
        cap.release()
        writer.release()
    logger.info("تم إنشاء فيديو مخفي الهوية: %s", dst)


if __name__ == "__main__":
    main()
