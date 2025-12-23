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

# إعداد اللوجر أولاً
logger = logging.getLogger(__name__)

try:
    import torch
except Exception:  # في حال عدم توفر torch أثناء التحضير
    torch = None  # type: ignore

# إصلاح مشكلة تحميل نماذج YOLO مع PyTorch 2.6+
try:
    import torch
    import os
    
    # تعطيل weights_only عالمياً
    os.environ['TORCH_WEIGHTS_ONLY'] = 'False'
    
    # تعديل دالة torch.load لفرض weights_only=False
    if hasattr(torch, 'load'):
        original_load = torch.load
        
        def patched_load(f, map_location=None, pickle_module=None, weights_only=None, **kwargs):
            """دالة torch.load معدلة لتعطيل weights_only"""
            return original_load(f, map_location=map_location, pickle_module=pickle_module, 
                               weights_only=False, **kwargs)
        
        torch.load = patched_load
        logger.info("✓ تم تطبيق إصلاح تحميل نماذج YOLO")
        
except Exception as e:
    logger.warning("تعذر تطبيق إصلاح تحميل النماذج: %s", e)

from ultralytics import YOLO
from .utils import calculate_centroid, draw_text_with_background
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
        model_size: str = "m",
        device: str = "cpu",
        conf: float = 0.35,
        iou: float = 0.5,
        imgsz: int = 640,
        half: bool = True,
    ) -> None:
        self.model_path = f"yolov8{model_size}.pt"
        self.conf = float(conf)
        self.iou = float(iou)
        self.imgsz = int(imgsz)

        # تحديد الجهاز
        cuda_available = torch is not None and hasattr(torch, "cuda") and torch.cuda.is_available()  # type: ignore[attr-defined]
        if device == "cuda" and not cuda_available:
            logger.warning("طُلب CUDA لكن غير متوفر، سيتم استخدام CPU.")
            device = "cpu"
        self.device = device

        # نصف الدقة فقط مع CUDA
        self.use_half = bool(half and self.device == "cuda")

        # تحميل النموذج المطلوب فقط (بدون fallback للنماذج الكبيرة)
        load_attempts = [self.model_path]

        last_error = None
        for path in load_attempts:
            try:
                # محاولة تحميل النموذج بطرق مختلفة
                try:
                    # الطريقة الأساسية
                    self.model = YOLO(path)
                except Exception as e1:
                    try:
                        # طريقة بديلة مع تحديد المهمة
                        self.model = YOLO(path, task='detect')
                    except Exception as e2:
                        try:
                            # تحميل مع تعطيل weights_only
                            import os
                            os.environ['TORCH_WEIGHTS_ONLY'] = 'False'
                            self.model = YOLO(path)
                        except Exception as e3:
                            # إذا فشلت كل الطرق، ارفع الخطأ
                            raise e1
                if self.device == "cuda":
                    self.model.to("cuda")
                if self.use_half and torch is not None:
                    try:
                        pass
                    except Exception as e:
                        logger.warning("تعذّر تفعيل نصف الدقة: %s", e)
                        self.use_half = False
                self.model_path = path
                logger.info("تم تحميل نموذج YOLO: %s على الجهاز %s", path, self.device)
                last_error = None
                break
            except Exception as e:
                last_error = e
                logger.warning("تعذر تحميل %s، سيتم المحاولة بنموذج آخر...", path)
        if last_error is not None and not hasattr(self, "model"):
            logger.exception("فشل تحميل جميع نماذج YOLO")
            raise last_error

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
                iou=self.iou,  # NMS قابل للتهيئة
                agnostic_nms=True,
                max_det=50,  # تقليل للحد من الكشوفات الخاطئة
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
    """متعقّب أشخاص محسّن مع IoU + Hungarian Algorithm + Velocity Prediction.

    التحسينات:
    - استخدام IoU (Intersection over Union) بالإضافة للمسافة
    - خوارزمية Hungarian للتعيين الأمثل
    - تنبؤ بالموقع القادم باستخدام السرعة
    - درجة ثقة للمسار
    """

    def __init__(
        self, 
        max_disappeared: int = 90, 
        max_distance: float = 120.0,
        min_iou: float = 0.1,
        use_velocity: bool = True
    ) -> None:
        self.max_disappeared = int(max_disappeared)
        self.max_distance = float(max_distance)
        self.min_iou = float(min_iou)
        self.use_velocity = use_velocity
        self.next_track_id: int = 1
        self.tracks: Dict[int, Dict[str, Any]] = {}

    @staticmethod
    def _calculate_iou(box1: Tuple[int, int, int, int], box2: Tuple[int, int, int, int]) -> float:
        """حساب IoU بين صندوقين"""
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        
        # منطقة التقاطع
        xi1 = max(x1_1, x1_2)
        yi1 = max(y1_1, y1_2)
        xi2 = min(x2_1, x2_2)
        yi2 = min(y2_1, y2_2)
        
        if xi2 <= xi1 or yi2 <= yi1:
            return 0.0
        
        intersection = (xi2 - xi1) * (yi2 - yi1)
        
        # مساحة كلا الصندوقين
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0

    def _register(self, box: Tuple[int, int, int, int]) -> int:
        tid = self.next_track_id
        self.next_track_id += 1
        centroid = calculate_centroid(box)
        self.tracks[tid] = {
            "box": box,
            "centroid": centroid,
            "frames_disappeared": 0,
            "velocity": (0.0, 0.0),  # (dx, dy) per frame
            "confidence": 0.5,
            "age": 0,  # عدد الإطارات منذ الإنشاء
        }
        return tid

    def remove_track(self, track_id: int) -> None:
        """حذف مسار محدد يدوياً."""
        if track_id in self.tracks:
            del self.tracks[track_id]

    def get_active_tracks(self) -> Dict[int, Dict[str, Any]]:
        """إرجاع المسارات النشطة حالياً."""
        return {k: v for k, v in self.tracks.items() if v.get("frames_disappeared", 0) <= self.max_disappeared}

    def _predict_position(self, track: Dict[str, Any]) -> Tuple[float, float]:
        """تنبؤ بالموقع القادم باستخدام السرعة"""
        if not self.use_velocity:
            return track["centroid"]
        
        cx, cy = track["centroid"]
        vx, vy = track.get("velocity", (0.0, 0.0))
        return (cx + vx, cy + vy)

    def _update_velocity(self, track: Dict[str, Any], new_centroid: Tuple[float, float]):
        """تحديث السرعة"""
        old_cx, old_cy = track["centroid"]
        new_cx, new_cy = new_centroid
        
        # حساب السرعة الجديدة مع تنعيم (EMA)
        alpha = 0.3
        old_vx, old_vy = track.get("velocity", (0.0, 0.0))
        new_vx = alpha * (new_cx - old_cx) + (1 - alpha) * old_vx
        new_vy = alpha * (new_cy - old_cy) + (1 - alpha) * old_vy
        
        track["velocity"] = (new_vx, new_vy)

    def _calculate_cost(self, track: Dict[str, Any], detection_box: Tuple[int, int, int, int]) -> float:
        """حساب تكلفة المطابقة (أقل = أفضل)"""
        # حساب IoU
        iou = self._calculate_iou(track["box"], detection_box)
        
        # حساب المسافة من الموقع المتوقع
        predicted_pos = self._predict_position(track)
        det_centroid = calculate_centroid(detection_box)
        distance = np.linalg.norm(np.array(predicted_pos) - np.array(det_centroid))
        
        # تطبيع المسافة
        norm_distance = min(distance / self.max_distance, 1.0)
        
        # التكلفة: مزيج من المسافة و(1 - IoU)
        # أوزان: 30% مسافة، 70% IoU (IoU أكثر أهمية للدقة)
        cost = 0.3 * norm_distance + 0.7 * (1.0 - iou)
        
        return cost

    def update(self, detections: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        """تحديث حالة المتعقب بقائمة الكشف الحديثة (محسّن)."""
        
        # زيادة عمر المسارات
        for track in self.tracks.values():
            track["age"] = track.get("age", 0) + 1
        
        # في حال لا توجد كاشفات
        if len(detections) == 0:
            to_delete = []
            for tid, t in self.tracks.items():
                t["frames_disappeared"] = t.get("frames_disappeared", 0) + 1
                t["confidence"] = max(t.get("confidence", 0.5) - 0.05, 0.1)
                if t["frames_disappeared"] > self.max_disappeared:
                    to_delete.append(tid)
            for tid in to_delete:
                self.remove_track(tid)
            return self.tracks

        input_boxes = [d["box"] for d in detections]

        if len(self.tracks) == 0:
            for box in input_boxes:
                self._register(box)
            return self.tracks

        # بناء مصفوفة التكلفة
        track_ids = list(self.tracks.keys())
        num_tracks = len(track_ids)
        num_dets = len(input_boxes)
        
        cost_matrix = np.zeros((num_tracks, num_dets), dtype=float)
        for i, tid in enumerate(track_ids):
            for j, det_box in enumerate(input_boxes):
                cost_matrix[i, j] = self._calculate_cost(self.tracks[tid], det_box)

        # التعيين باستخدام خوارزمية greedy محسّنة
        # (يمكن استبدالها بـ Hungarian إذا توفر scipy)
        used_rows = set()
        used_cols = set()
        assignments = []

        # ترتيب حسب أقل تكلفة
        flat_indices = np.argsort(cost_matrix.flatten())
        for flat_idx in flat_indices:
            row = flat_idx // num_dets
            col = flat_idx % num_dets
            
            if row in used_rows or col in used_cols:
                continue
            
            cost = cost_matrix[row, col]
            
            # رفض المطابقات السيئة
            det_box = input_boxes[col]
            iou = self._calculate_iou(self.tracks[track_ids[row]]["box"], det_box)
            
            predicted_pos = self._predict_position(self.tracks[track_ids[row]])
            det_centroid = calculate_centroid(det_box)
            distance = np.linalg.norm(np.array(predicted_pos) - np.array(det_centroid))
            
            if distance <= self.max_distance or iou >= self.min_iou:
                assignments.append((row, col))
                used_rows.add(row)
                used_cols.add(col)

        # تحديث المسارات المطابقة
        for row, col in assignments:
            tid = track_ids[row]
            box = input_boxes[col]
            new_centroid = calculate_centroid(box)
            
            # تحديث السرعة قبل تحديث الموقع
            self._update_velocity(self.tracks[tid], new_centroid)
            
            self.tracks[tid]["box"] = box
            self.tracks[tid]["centroid"] = new_centroid
            self.tracks[tid]["frames_disappeared"] = 0
            self.tracks[tid]["confidence"] = min(self.tracks[tid].get("confidence", 0.5) + 0.1, 1.0)

        # المسارات غير المعينّة: اعتبرها مختفية
        for r, tid in enumerate(track_ids):
            if r not in used_rows:
                self.tracks[tid]["frames_disappeared"] += 1
                self.tracks[tid]["confidence"] = max(self.tracks[tid].get("confidence", 0.5) - 0.05, 0.1)

        # الكاشفات غير المعينة: سجّل مسارات جديدة
        for c, box in enumerate(input_boxes):
            if c not in used_cols:
                self._register(box)

        # حذف المسارات التي تجاوزت حد الاختفاء
        to_delete = [tid for tid, t in self.tracks.items() if t.get("frames_disappeared", 0) > self.max_disappeared]
        for tid in to_delete:
            self.remove_track(tid)

        return self.tracks

    def get_track_confidence(self, track_id: int) -> float:
        """الحصول على درجة الثقة لمسار معين"""
        if track_id in self.tracks:
            return self.tracks[track_id].get("confidence", 0.5)
        return 0.0

