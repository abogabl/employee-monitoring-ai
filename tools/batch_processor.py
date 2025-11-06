"""
معالجة دفعات من الفيديوهات: كشف وتتبع وحفظ فيديو ناتج.
مثال:
python batch_processor.py --input-dir videos/ --output-dir results/ --parallel 4
"""
from __future__ import annotations

import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List

import cv2
from tqdm import tqdm

from src.detection_tracking import PersonDetector, PersonTracker
from src.utils import draw_text_with_background

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("batch_processor")


def process_one(video: Path, out_dir: Path, device: str, imgsz: int, conf: float) -> str:
    try:
        cap = cv2.VideoCapture(str(video))
        if not cap.isOpened():
            return f"FAILED open {video}"
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720)
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{video.stem}_processed.mp4"
        writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))

        det = PersonDetector(model_size="n", device=device, conf=conf, imgsz=imgsz, half=(device=="cuda"))
        trk = PersonTracker(max_disappeared=30, max_distance=75)

        pbar = tqdm(total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0), desc=video.name, unit="f")
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            dets = det.detect(frame)
            tracks = trk.update(dets)
            vis = frame.copy()
            for tid, t in tracks.items():
                x1, y1, x2, y2 = t["box"]
                cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
                draw_text_with_background(vis, f"ID {tid}", (x1, max(15, y1-5)))
            writer.write(vis)
            pbar.update(1)
        pbar.close()
        cap.release()
        writer.release()
        return str(out_path)
    except Exception as e:
        return f"FAILED {video}: {e}"


def main() -> None:
    ap = argparse.ArgumentParser(description="معالجة دفعات فيديو")
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--parallel", type=int, default=2)
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--conf", type=float, default=0.5)
    args = ap.parse_args()

    inp = Path(args.input_dir)
    out = Path(args.output_dir)
    videos = [p for p in inp.glob("**/*") if p.suffix.lower() in {".mp4", ".avi", ".mov", ".mkv"}]
    if not videos:
        logger.error("لا توجد فيديوهات")
        return

    results: List[str] = []
    with ThreadPoolExecutor(max_workers=max(1, args.parallel)) as ex:
        futs = [ex.submit(process_one, v, out, args.device, args.imgsz, args.conf) for v in videos]
        for f in tqdm(as_completed(futs), total=len(futs), desc="Batch"):
            results.append(f.result())

    for r in results:
        logger.info(r)


if __name__ == "__main__":
    main()
