"""
تحويل صيغ الفيديو باستخدام ffmpeg إن وُجد، وإلا OpenCV.
مثال:
python convert_video.py --input video.avi --output video.mp4 --codec h264 --resize 1280x720
"""
from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

import cv2

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("convert_video")


def parse_size(s: Optional[str]) -> Optional[Tuple[int, int]]:
    if not s:
        return None
    w, h = s.lower().split("x")
    return int(w), int(h)


def convert_with_ffmpeg(inp: Path, out: Path, codec: str, size: Optional[Tuple[int, int]]) -> bool:
    if shutil.which("ffmpeg") is None:
        return False
    cmd = ["ffmpeg", "-y", "-i", str(inp)]
    if size:
        cmd += ["-vf", f"scale={size[0]}:{size[1]}"]
    if codec.lower() in {"h264", "libx264"}:
        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    elif codec.lower() in {"h265", "libx265"}:
        cmd += ["-c:v", "libx265"]
    else:
        cmd += ["-c:v", "libx264"]
    cmd += [str(out)]
    try:
        subprocess.check_call(cmd)
        return True
    except subprocess.CalledProcessError as e:
        logger.warning("ffmpeg فشل: %s", e)
        return False


def convert_with_opencv(inp: Path, out: Path, size: Optional[Tuple[int, int]]) -> bool:
    cap = cv2.VideoCapture(str(inp))
    if not cap.isOpened():
        logger.error("تعذر فتح %s", inp)
        return False
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if size:
        w, h = size
    fourcc = cv2.VideoWriter_fourcc(*"mp4v") if out.suffix.lower() == ".mp4" else cv2.VideoWriter_fourcc(*"XVID")
    writer = cv2.VideoWriter(str(out), fourcc, fps, (w, h))
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if size and (frame.shape[1] != w or frame.shape[0] != h):
                frame = cv2.resize(frame, (w, h), interpolation=cv2.INTER_AREA)
            writer.write(frame)
        return True
    finally:
        cap.release()
        writer.release()


def main() -> None:
    ap = argparse.ArgumentParser(description="تحويل صيغ الفيديو")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--codec", default="h264")
    ap.add_argument("--resize", default=None, help="مثال 1280x720")
    args = ap.parse_args()

    inp = Path(args.input)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    size = parse_size(args.resize)

    if convert_with_ffmpeg(inp, out, args.codec, size):
        logger.info("تم التحويل عبر ffmpeg: %s -> %s", inp, out)
        return
    ok = convert_with_opencv(inp, out, size)
    if ok:
        logger.info("تم التحويل عبر OpenCV: %s -> %s", inp, out)
    else:
        logger.error("فشل التحويل")


if __name__ == "__main__":
    main()
