"""
مقارنة نماذج YOLOv8 على فيديو واحد وقياس FPS واستخدام الذاكرة.
مثال:
python benchmark_models.py --video test.mp4 --models yolov8n,yolov8s,yolov8m,yolov8l --device cpu
"""
from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path
from typing import List

import cv2
import numpy as np

try:
    import torch  # type: ignore
except Exception:
    torch = None  # type: ignore

from ultralytics import YOLO

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("benchmark_models")


def bench_model(video: Path, model_name: str, device: str = "cpu", warmup: int = 30, max_frames: int = 300) -> dict:
    model = YOLO(f"{model_name}.pt")
    if device == "cuda":
        model.to("cuda")
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {video}")
    # warmup
    for _ in range(warmup):
        ok, frame = cap.read()
        if not ok:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
        model.predict(frame, imgsz=640, conf=0.5, device=device, verbose=False)
    # measure
    frames = 0
    t0 = time.time()
    while frames < max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        model.predict(frame, imgsz=640, conf=0.5, device=device, verbose=False)
        frames += 1
    dt = time.time() - t0
    fps = frames / dt if dt > 0 else 0.0
    gpu_mem = None
    if device == "cuda" and torch is not None and torch.cuda.is_available():
        try:
            gpu_mem = f"{torch.cuda.max_memory_allocated() / (1024**3):.1f} GB"
            torch.cuda.reset_peak_memory_stats()
        except Exception:
            gpu_mem = None
    size_mb = Path(f"{model_name}.pt").stat().st_size / (1024 ** 2) if Path(f"{model_name}.pt").exists() else None
    cap.release()
    return {
        "Model": model_name,
        "FPS": round(fps, 1),
        "mAP": "-",  # يتطلب مجموعة تقييم، غير محسوب هنا
        "Size": f"{size_mb:.0f} MB" if size_mb else "-",
        "GPU Mem": gpu_mem or "-",
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="مقارنة نماذج YOLOv8")
    ap.add_argument("--video", required=True)
    ap.add_argument("--models", required=True, help="قائمة نماذج مفصولة بفواصل مثل yolov8n,yolov8s")
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    args = ap.parse_args()

    video = Path(args.video)
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    rows: List[dict] = []
    for m in models:
        rows.append(bench_model(video, m, device=args.device))
    # طباعة جدول بسيط
    hdr = ["Model", "FPS", "mAP", "Size", "GPU Mem"]
    print("| " + " | ".join(hdr) + " |")
    print("|" + "-" * (len(" | ".join(hdr)) + 2) + "|")
    for r in rows:
        print("| " + " | ".join(str(r[h]) for h in hdr) + " |")


if __name__ == "__main__":
    main()
