"""
وحدات الكشف والتتبع للأشخاص باستخدام YOLOv8.
- PersonDetector: يستخدم ultralytics YOLOv8 للكشف عن الأشخاص فقط (class=0)
- PersonTracker: تتبع بسيط قائم على المسافة ومراكز الصناديق مع إدارة الاختفاء المؤقت
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any

import cv2
import numpy as np

try:
    import torch
except Exception:  # في حال عدم توفر torch أثناء التحضير
    torch = None  # type: ignore

from ultralytics import YOLO
try:
    # PyTorch 2.6+: default weights_only=True requires allow-listing Ultralytics classes
    from torch.serialization import add_safe_globals  # type: ignore
    from ultralytics.nn.tasks import DetectionModel  # type: ignore
    try:
        add_safe_globals([DetectionModel])
    except Exception:
        pass
except Exception:
    # إذا كانت الإصدارات أقدم أو لم تتوفر الدوال، نتجاهل هذا التهيئة
    pass

from .utils import calculate_centroid, draw_text_with_background


# إعداد اللوجر
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


class PersonDetector:
    """كاشف أشخاص باستخدام YOLOv8.

    المعلمات:
    - model_size: حرف حجم النموذج من عائلة YOLOv8 (n, s, m, l, x)
    - device: "cpu" أو "cuda" (يُفحص تلقائياً توفر CUDA)
    - conf: عتبة الثقة للكشف
    - imgsz: حجم الإدخال للنموذج
    - half: استخدام نصف الدقة (FP16) عند توفر CUDA لتسريع الاستدلال
    """

    def __init__(
        self,
        model_size: str = "n",
        device: str = "cpu",
        conf: float = 0.5,
        imgsz: int = 640,
        half: bool = True,
    ) -> None:
        self.model_path = f"yolov8{model_size}.pt"
        self.conf = float(conf)
        self.imgsz = int(imgsz)

        # تحديد الجهاز
        cuda_available = torch is not None and hasattr(torch, "cuda") and torch.cuda.is_available()  # type: ignore[attr-defined]
        if device == "cuda" and not cuda_available:
            logger.warning("طُلب CUDA لكن غير متوفر، سيتم استخدام CPU.")
            device = "cpu"
        self.device = device

        # نصف الدقة فقط مع CUDA
        self.use_half = bool(half and self.device == "cuda")

        # تحميل النموذج
        try:
            self.model = YOLO(self.model_path)
            if self.device == "cuda":
                self.model.to("cuda")
            if self.use_half and torch is not None:
                try:
                    # بعض نماذج ultralytics تدعم half تلقائياً من خلال بارامتر predict
                    # لكن نُبقي علماً داخلياً للاستخدام
                    pass
                except Exception as e:
                    logger.warning("تعذّر تفعيل نصف الدقة: %s", e)
                    self.use_half = False
            logger.info("تم تحميل نموذج YOLO: %s على الجهاز %s", self.model_path, self.device)
        except Exception as e:
            logger.exception("فشل تحميل نموذج YOLO: %s", e)
            raise

    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """تنفيذ الكشف على إطار واحد وإرجاع قائمة كائنات أشخاص.

        يرجع عناصر بالشكل: {"box": (x1,y1,x2,y2), "conf": float, "class": int}
        """
        if frame is None or frame.size == 0:
            return []
        try:
            results = self.model.predict(
                frame,
                imgsz=self.imgsz,
                conf=self.conf,
                device=self.device,
                classes=[0],  # person فقط
                half=self.use_half,
                verbose=False,
                stream=False,
            )
            detections: List[Dict[str, Any]] = []
            if not results:
                return detections
            r = results[0]
            if r is None or r.boxes is None:
                return detections
            for b in r.boxes:
                # xyxy، conf، cls
                xyxy = b.xyxy[0].detach().cpu().numpy().astype(int)
                x1, y1, x2, y2 = map(int, xyxy.tolist())
                conf = float(b.conf[0].detach().cpu().item()) if hasattr(b, "conf") else 0.0
                cls_id = int(b.cls[0].detach().cpu().item()) if hasattr(b, "cls") else 0
                detections.append({"box": (x1, y1, x2, y2), "conf": conf, "class": cls_id})
            return detections
        except Exception as e:
            logger.exception("خطأ أثناء الكشف: %s", e)
            return []

    @staticmethod
    def draw_boxes(
        frame: np.ndarray,
        detections: List[Dict[str, Any]],
        color: Tuple[int, int, int] = (0, 255, 0),
    ) -> np.ndarray:
        """رسم صناديق الكشف على الإطار."""
        for det in detections:
            x1, y1, x2, y2 = det["box"]
            conf = det.get("conf", 0.0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label = f"person {conf:.2f}"
            draw_text_with_background(frame, label, (x1, max(15, y1)))
        return frame


class PersonTracker:
    """متعقّب أشخاص بسيط باستخدام مراكز الصناديق والمسافة الإقليدية.

    - يمنح ID ثابت لكل شخص طالما المسافة ضمن حد معين.
    - يدير حالات الاختفاء المؤقت عبر عداد frames_disappeared.
    - يحذف المسارات التي تتجاوز حد الاختفاء.
    """

    def __init__(self, max_disappeared: int = 30, max_distance: float = 50.0) -> None:
        self.max_disappeared = int(max_disappeared)
        self.max_distance = float(max_distance)
        self.next_track_id: int = 1
        self.tracks: Dict[int, Dict[str, Any]] = {}

    def _register(self, box: Tuple[int, int, int, int]) -> int:
        tid = self.next_track_id
        self.next_track_id += 1
        self.tracks[tid] = {
            "box": box,
            "centroid": calculate_centroid(box),
            "frames_disappeared": 0,
        }
        return tid

    def remove_track(self, track_id: int) -> None:
        """حذف مسار محدد يدوياً."""
        if track_id in self.tracks:
            del self.tracks[track_id]

    def get_active_tracks(self) -> Dict[int, Dict[str, Any]]:
        """إرجاع المسارات النشطة حالياً."""
        return {k: v for k, v in self.tracks.items() if v.get("frames_disappeared", 0) <= self.max_disappeared}

    def update(self, detections: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        """تحديث حالة المتعقب بقائمة الكشف الحديثة.

        يستخدم أبسط تعيين قائم على أقرب مركز ضمن مسافة قصوى.
        يرجع قاموس: track_id -> {box, centroid, frames_disappeared}
        """
        # في حال لا توجد كاشفات
        if len(detections) == 0:
            # زيادة عداد الاختفاء لكل مسار
            to_delete = []
            for tid, t in self.tracks.items():
                t["frames_disappeared"] = t.get("frames_disappeared", 0) + 1
                if t["frames_disappeared"] > self.max_disappeared:
                    to_delete.append(tid)
            for tid in to_delete:
                self.remove_track(tid)
            return self.tracks

        input_boxes = [d["box"] for d in detections]
        input_centroids = [calculate_centroid(b) for b in input_boxes]

        if len(self.tracks) == 0:
            for box in input_boxes:
                self._register(box)
            return self.tracks

        # تحضير مصفوفة المسافات بين المسارات الحالية والكاشفات
        track_ids = list(self.tracks.keys())
        track_centroids = [self.tracks[tid]["centroid"] for tid in track_ids]

        D = np.zeros((len(track_centroids), len(input_centroids)), dtype=float)
        for i, tc in enumerate(track_centroids):
            for j, ic in enumerate(input_centroids):
                D[i, j] = np.linalg.norm(np.array(tc) - np.array(ic))

        # تعيين greedy: اختيار أقرب كشف لكل مسار إن كانت المسافة مقبولة
        used_rows = set()
        used_cols = set()

        rows = np.argsort(D.min(axis=1))  # ترتيب حسب أقرب كشف
        for row in rows:
            if row in used_rows:
                continue
            col = int(np.argmin(D[row]))
            if col in used_cols:
                continue
            if D[row, col] <= self.max_distance:
                tid = track_ids[row]
                box = input_boxes[col]
                self.tracks[tid]["box"] = box
                self.tracks[tid]["centroid"] = input_centroids[col]
                self.tracks[tid]["frames_disappeared"] = 0
                used_rows.add(row)
                used_cols.add(col)

        # المسارات غير المعينّة: اعتبرها مختفية
        for r, tid in enumerate(track_ids):
            if r not in used_rows:
                self.tracks[tid]["frames_disappeared"] = self.tracks[tid].get("frames_disappeared", 0) + 1

        # الكاشفات غير المعينة: سجّل مسارات جديدة
        for c, box in enumerate(input_boxes):
            if c not in used_cols:
                self._register(box)

        # حذف المسارات التي تجاوزت حد الاختفاء
        to_delete = [tid for tid, t in self.tracks.items() if t.get("frames_disappeared", 0) > self.max_disappeared]
        for tid in to_delete:
            self.remove_track(tid)

        return self.tracks
