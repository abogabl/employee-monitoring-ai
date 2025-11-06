"""
تجربة نظام التعرف على الأنشطة:
- كشف أشخاص (YOLOv8)
- تتبع (PersonTracker)
- كشف أشياء قريبة (YOLOv8 لأصناف: هاتف/كمبيوتر)
- تحليل وضعية (MediaPipe Pose)
- تصنيف النشاط مع تنعيم زمني
- عرض بصري وإحصاءات بسيطة

تشغيل:
py test_activities.py --video videos/sample.mp4 --device cpu --fps-hint 25
"""
from __future__ import annotations

import argparse
import logging
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from ultralytics import YOLO

from src.detection_tracking import PersonDetector, PersonTracker
from src.activity_recognition import ActivityRecognizer
from src.activity_validator import compute_metrics, load_ground_truth_csv, pretty_print_metrics
from src.activity_rules import DEFAULT_ACTIVITIES
from src.utils import draw_text_with_background

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("test_activities")

# الأصناف ذات الصلة من COCO
OBJECT_NAME_SET = {
    "cell phone", "phone", "mobile",
    "laptop", "keyboard", "mouse", "monitor", "tv", "screen"
}


def build_object_detector(model_size: str = "n", device: str = "cpu") -> YOLO:
    """إنشاء نموذج YOLOv8 للأشياء العامة (COCO)."""
    model = YOLO(f"yolov8{model_size}.pt")
    if device == "cuda":
        model.to("cuda")
    return model


def detect_objects(model: YOLO, frame: np.ndarray, device: str = "cpu", imgsz: int = 640, conf: float = 0.35) -> List[Dict[str, Any]]:
    """كشف الأشياء وتصفيتها على الأصناف ذات الصلة، وإرجاع قائمة قواميس تتضمن الاسم."""
    try:
        results = model.predict(frame, imgsz=imgsz, conf=conf, device=device, verbose=False)
    except Exception as e:
        logger.exception("فشل كشف الأشياء: %s", e)
        return []
    dets: List[Dict[str, Any]] = []
    if not results:
        return dets
    r = results[0]
    if r is None or r.boxes is None:
        return dets
    names = r.names if hasattr(r, "names") else {}
    for b in r.boxes:
        xyxy = b.xyxy[0].detach().cpu().numpy().astype(int)
        x1, y1, x2, y2 = map(int, xyxy.tolist())
        conf_v = float(b.conf[0].detach().cpu().item()) if hasattr(b, "conf") else 0.0
        cls_id = int(b.cls[0].detach().cpu().item()) if hasattr(b, "cls") else -1
        name = str(names.get(cls_id, "")).lower()
        if name in OBJECT_NAME_SET:
            dets.append({"box": (x1, y1, x2, y2), "conf": conf_v, "class": cls_id, "name": name})
    return dets


def main() -> None:
    parser = argparse.ArgumentParser(description="اختبار التعرف على الأنشطة من فيديو")
    parser.add_argument("--video", required=True, help="مسار الفيديو")
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"], help="جهاز التنفيذ لليولو")
    parser.add_argument("--fps-hint", type=float, default=25.0, help="تلميح FPS للتنعيم الزمني")
    parser.add_argument("--save", action="store_true", help="حفظ فيديو الإخراج")
    parser.add_argument("--gt-csv", type=str, default="", help="ملف ground truth اختياري بصيغة CSV (track_id,activity)")
    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        logger.error("فيديو غير موجود: %s", video_path)
        return

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        logger.error("تعذر فتح الفيديو: %s", video_path)
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or args.fps_hint
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    writer = None
    if args.save:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out_path = video_path.parent / f"{video_path.stem}_activities.mp4"
        writer = cv2.VideoWriter(str(out_path), fourcc, fps, (width, height))

    # كاشف الأشخاص ومتتبّعهم
    person_detector = PersonDetector(model_size="n", device=args.device, conf=0.5, imgsz=640, half=(args.device=="cuda"))
    tracker = PersonTracker(max_disappeared=30, max_distance=75)

    # كاشف الأشياء
    object_detector = build_object_detector(model_size="n", device=args.device)

    # مميز الأنشطة
    recognizer = ActivityRecognizer(use_pose=True, use_objects=True, use_motion=True, smoothing_seconds=5.0, fps_hint=fps)

    # إحصاءات بسيطة
    activity_counts = defaultdict(int)
    track_activity: Dict[int, str] = {}
    gt = None
    if args.gt_csv:
        rows = load_ground_truth_csv(args.gt_csv)
        if rows:
            gt = {tid: act for tid, act in rows}

    prev_time = time.time()
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            now = time.time()
            # كشف الأشخاص وتتبعهم
            person_dets = person_detector.detect(frame)
            tracks = tracker.update(person_dets)

            # كشف الأشياء ذات الصلة
            obj_dets = detect_objects(object_detector, frame, device=args.device, imgsz=640, conf=0.35)

            vis = frame.copy()
            # لكل مسار شخص، صنّف النشاط
            for tid, t in tracks.items():
                box = t["box"]
                result = recognizer.process_person(frame, box, t, obj_dets, track_id=tid, curr_time=now)
                activity_counts[result.activity] += 1
                track_activity[tid] = result.activity

                # رسم الصناديق والنشاط
                x1, y1, x2, y2 = box
                cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
                label = f"ID {tid} | {result.activity} ({result.confidence:.2f})"
                draw_text_with_background(vis, label, (x1, max(15, y1 - 5)))

            # رسم بعض الأشياء المكتشفة للإيضاح
            for d in obj_dets[:10]:
                x1, y1, x2, y2 = d["box"]
                cv2.rectangle(vis, (x1, y1), (x2, y2), (255, 255, 0), 1)
                draw_text_with_background(vis, d["name"], (x1, max(15, y1 - 5)), color=(0, 255, 255))

            # FPS
            dt = now - prev_time
            prev_time = now
            fps_text = f"FPS: {1.0 / dt:.1f}" if dt > 0 else "FPS: -"
            draw_text_with_background(vis, fps_text, (10, 25), color=(0, 255, 255))

            if writer is not None:
                writer.write(vis)
            cv2.imshow("Activity Recognition", vis)
            if cv2.waitKey(1) & 0xFF == 27:
                break
    except KeyboardInterrupt:
        logger.info("تم الإيقاف بواسطة المستخدم.")
    finally:
        cap.release()
        if writer is not None:
            writer.release()
        cv2.destroyAllWindows()

    # إحصاءات
    total = sum(activity_counts.values())
    if total > 0:
        logger.info("توزيع الأنشطة:")
        for act in DEFAULT_ACTIVITIES:
            c = activity_counts[act]
            logger.info("- %s: %.1f%%", act, 100.0 * c / total)

    # تقييم دقة إذا وُجد ground truth
    if gt:
        y_true = []
        y_pred = []
        for tid, true_act in gt.items():
            if not tid.isdigit():
                continue
            tid_i = int(tid)
            pred = track_activity.get(tid_i, "idle")
            y_true.append(true_act)
            y_pred.append(pred)
        if y_true and y_pred:
            metrics = compute_metrics(y_true, y_pred)
            pretty_print_metrics(metrics)


if __name__ == "__main__":
    main()
