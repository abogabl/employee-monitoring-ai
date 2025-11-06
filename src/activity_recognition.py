"""
نظام التعرف على أنشطة الموظفين باستخدام MediaPipe Pose + YOLO للأشياء + قواعد ذكية + تنعيم زمني.
"""
from __future__ import annotations

import logging
import math
from collections import Counter, deque
from dataclasses import dataclass
from typing import Any, Deque, Dict, List, Optional, Tuple

import cv2
import numpy as np

from .activity_rules import ActivityRules
from .utils import calculate_centroid

try:
    import mediapipe as mp  # type: ignore
except Exception as e:  # pragma: no cover
    mp = None  # type: ignore

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


# أسماء فئات COCO ذات الصلة (قد تختلف بحسب النموذج)
COCO_NAMES = {
    63: "laptop",
    64: "mouse",
    66: "keyboard",
    67: "cell phone",
    62: "tv",  # بديل عن monitor
}
MONITOR_NAMES = {"tv", "monitor", "screen"}
COMPUTER_NAMES = {"laptop", "keyboard", "mouse", *MONITOR_NAMES}
PHONE_NAMES = {"cell phone", "phone", "mobile"}


@dataclass
class ActivityResult:
    activity: str
    confidence: float
    details: Dict[str, Any]


def _euclidean(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return float(math.hypot(p1[0] - p2[0], p1[1] - p2[1]))


class ActivityRecognizer:
    """يتعرف على النشاط عبر دمج معلومات الوضعية والأشياء والحركة مع قواعد وتنعيم زمني."""

    def __init__(
        self,
        use_pose: bool = True,
        use_objects: bool = True,
        use_motion: bool = True,
        smoothing_seconds: float = 5.0,
        fps_hint: float = 25.0,
        rules: Optional[ActivityRules] = None,
    ) -> None:
        self.use_pose = use_pose
        self.use_objects = use_objects
        self.use_motion = use_motion
        self.rules = rules or ActivityRules()

        # نافذة تنعيم بعدد إطارات تقديري
        self.window_size = max(1, int(smoothing_seconds * max(fps_hint, 1.0)))
        self.histories: Dict[int, Deque[ActivityResult]] = {}
        self.prev_boxes: Dict[int, Tuple[int, int, int, int]] = {}
        self.prev_times: Dict[int, float] = {}

        # تهيئة MediaPipe Pose
        self.pose = None
        if self.use_pose:
            if mp is None:
                logger.warning("لم يتم تثبيت mediapipe؛ سيتم تعطيل تحليل الوضعيات.")
                self.use_pose = False
            else:
                self.mp_pose = mp.solutions.pose  # type: ignore
                self.pose = self.mp_pose.Pose(static_image_mode=False, model_complexity=1, enable_segmentation=False)

    # ----------------------------- Pose -----------------------------
    def analyze_pose(self, image: np.ndarray, person_box: Tuple[int, int, int, int]) -> Dict[str, Any]:
        """تحليل وضعية الشخص داخل الصندوق لإستنتاج الجلوس/الوقوف ووضع اليدين."""
        if not self.use_pose or self.pose is None:
            return {"sitting": False, "hand_near_face": False, "hands_forward": False, "body_angle": 0.0, "pose_confidence": 0.0}

        x1, y1, x2, y2 = person_box
        crop = image[max(0, y1):max(0, y2), max(0, x1):max(0, x2)]
        if crop.size == 0:
            return {"sitting": False, "hand_near_face": False, "hands_forward": False, "body_angle": 0.0, "pose_confidence": 0.0}

        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        res = self.pose.process(rgb)
        if not res.pose_landmarks:
            return {"sitting": False, "hand_near_face": False, "hands_forward": False, "body_angle": 0.0, "pose_confidence": 0.0}

        lm = res.pose_landmarks.landmark
        H, W = crop.shape[:2]

        def L(name: int) -> Tuple[float, float]:
            p = lm[name]
            return p.x * W, p.y * H

        # نقاط مهمة
        NOSE = self.mp_pose.PoseLandmark.NOSE  # type: ignore[attr-defined]
        LEFT_EAR = self.mp_pose.PoseLandmark.LEFT_EAR  # type: ignore[attr-defined]
        RIGHT_EAR = self.mp_pose.PoseLandmark.RIGHT_EAR  # type: ignore[attr-defined]
        LEFT_WRIST = self.mp_pose.PoseLandmark.LEFT_WRIST  # type: ignore[attr-defined]
        RIGHT_WRIST = self.mp_pose.PoseLandmark.RIGHT_WRIST  # type: ignore[attr-defined]
        LEFT_SHOULDER = self.mp_pose.PoseLandmark.LEFT_SHOULDER  # type: ignore[attr-defined]
        RIGHT_SHOULDER = self.mp_pose.PoseLandmark.RIGHT_SHOULDER  # type: ignore[attr-defined]
        LEFT_HIP = self.mp_pose.PoseLandmark.LEFT_HIP  # type: ignore[attr-defined]
        RIGHT_HIP = self.mp_pose.PoseLandmark.RIGHT_HIP  # type: ignore[attr-defined]
        LEFT_KNEE = self.mp_pose.PoseLandmark.LEFT_KNEE  # type: ignore[attr-defined]
        RIGHT_KNEE = self.mp_pose.PoseLandmark.RIGHT_KNEE  # type: ignore[attr-defined]

        nose = L(NOSE)
        le, re = L(LEFT_EAR), L(RIGHT_EAR)
        lw, rw = L(LEFT_WRIST), L(RIGHT_WRIST)
        ls, rs = L(LEFT_SHOULDER), L(RIGHT_SHOULDER)
        lh, rh = L(LEFT_HIP), L(RIGHT_HIP)
        lk, rk = L(LEFT_KNEE), L(RIGHT_KNEE)

        # الجلوس: المسافة الرأسية بين الورك والركبة صغيرة مقارنة بطول الجذع
        hip_mid = ((lh[0] + rh[0]) / 2, (lh[1] + rh[1]) / 2)
        knee_mid = ((lk[0] + rk[0]) / 2, (lk[1] + rk[1]) / 2)
        shoulder_mid = ((ls[0] + rs[0]) / 2, (ls[1] + rs[1]) / 2)
        trunk_len = _euclidean(shoulder_mid, hip_mid) + 1e-6
        knee_hip = abs(knee_mid[1] - hip_mid[1])
        sitting = knee_hip < 0.6 * trunk_len

        # اليد قرب الوجه: أي من الرسغين ضمن مسافة من الأنف/الأذن
        face_center = ((nose[0] + le[0] + re[0]) / 3, (nose[1] + le[1] + re[1]) / 3)
        wrist_face_dist = min(_euclidean(lw, face_center), _euclidean(rw, face_center))
        face_size = max(_euclidean(le, re), _euclidean(nose, ((le[0]+re[0])/2, (le[1]+re[1])/2))) + 1e-6
        hand_near_face = wrist_face_dist < 1.6 * face_size

        # اليدان أمام الجسم: الرسغان أمام منتصف الكتفين أفقياً (نحو الأمام) وصناعياً داخل نطاق الظهر-الصدر
        body_center_x = (ls[0] + rs[0]) / 2
        hands_forward = (lw[0] > body_center_x and rw[0] > body_center_x) or (lw[0] < body_center_x and rw[0] < body_center_x)

        # زاوية الجسم (ميل الجذع)
        dy = shoulder_mid[1] - hip_mid[1]
        dx = shoulder_mid[0] - hip_mid[0]
        body_angle = math.degrees(math.atan2(dy, dx))  # قيمة تقريبية

        pose_confidence = float(res.pose_landmarks.landmark[self.mp_pose.PoseLandmark.NOSE].visibility)  # type: ignore[index]

        return {
            "sitting": bool(sitting),
            "hand_near_face": bool(hand_near_face),
            "hands_forward": bool(hands_forward),
            "body_angle": float(body_angle),
            "pose_confidence": float(pose_confidence),
        }

    # ----------------------------- Objects -----------------------------
    def detect_nearby_objects(
        self,
        yolo_detections: List[Dict[str, Any]],
        person_box: Tuple[int, int, int, int],
        max_distance: int = 200,
    ) -> Dict[str, Any]:
        """تحديد الأشياء القريبة من الشخص ضمن مسافة بكسلية معينة."""
        x1, y1, x2, y2 = person_box
        pc = calculate_centroid(person_box)
        found: List[Dict[str, Any]] = []
        phone_nearby = False
        computer_nearby = False

        for det in yolo_detections:
            cls_id = int(det.get("class", -1))
            name = str(det.get("name", COCO_NAMES.get(cls_id, ""))).lower()
            if not name:
                continue
            if name not in PHONE_NAMES and name not in COMPUTER_NAMES and name not in MONITOR_NAMES:
                continue
            bx1, by1, bx2, by2 = det.get("box", (0, 0, 0, 0))
            oc = calculate_centroid((bx1, by1, bx2, by2))
            dist = _euclidean(pc, oc)
            if dist <= max_distance:
                item = {"name": name, "box": (bx1, by1, bx2, by2), "distance": float(dist), "conf": float(det.get("conf", 0.0))}
                found.append(item)
                if name in PHONE_NAMES:
                    phone_nearby = True
                if name in COMPUTER_NAMES or name in MONITOR_NAMES:
                    computer_nearby = True

        return {"phone_nearby": phone_nearby, "computer_nearby": computer_nearby, "objects_list": found}

    # ----------------------------- Motion -----------------------------
    @staticmethod
    def calculate_motion(current_box: Tuple[int, int, int, int], previous_box: Optional[Tuple[int, int, int, int]], time_delta: float) -> float:
        """تقدير مستوى الحركة بين صندوقين عبر إزاحة المركز، طبيعي إلى قطر الصندوق والزمن (0..1)."""
        if previous_box is None or time_delta <= 0:
            return 0.0
        cc = np.array(calculate_centroid(current_box), dtype=float)
        pc = np.array(calculate_centroid(previous_box), dtype=float)
        disp = float(np.linalg.norm(cc - pc))
        w = current_box[2] - current_box[0]
        h = current_box[3] - current_box[1]
        diag = math.hypot(w, h) + 1e-6
        speed = disp / diag / max(time_delta, 1e-3)  # إزاحة نسبة/ثانية
        return float(max(0.0, min(speed, 1.0)))

    # ----------------------------- Classify -----------------------------
    def classify_activity(self, pose_info: Dict[str, Any], objects_info: Dict[str, Any], motion_level: float) -> ActivityResult:
        """دمج الميزات وتطبيق القواعد لإرجاع النشاط بثقة."""
        features = {
            **pose_info,
            **objects_info,
            "motion_level": float(motion_level),
        }
        activity, score, all_scores = self.rules.classify(features)
        return ActivityResult(activity=activity, confidence=float(score), details={"features": features, "scores": all_scores})

    # ----------------------------- Pipeline -----------------------------
    def process_person(
        self,
        frame: np.ndarray,
        person_box: Tuple[int, int, int, int],
        track_history: Dict[str, Any],
        yolo_detections: List[Dict[str, Any]],
        track_id: Optional[int] = None,
        curr_time: Optional[float] = None,
    ) -> ActivityResult:
        """معالجة شخص واحد: تحليل الوضعية، تحديد الأشياء القريبة، تقدير الحركة، تصنيف وتنعيم زمني."""
        # Pose
        pose_info = self.analyze_pose(frame, person_box) if self.use_pose else {"sitting": False, "hand_near_face": False, "hands_forward": False, "body_angle": 0.0, "pose_confidence": 0.0}
        # Objects
        objects_info = self.detect_nearby_objects(yolo_detections, person_box) if self.use_objects else {"phone_nearby": False, "computer_nearby": False, "objects_list": []}
        # Motion
        if self.use_motion and track_id is not None:
            prev_box = self.prev_boxes.get(track_id)
            prev_time = self.prev_times.get(track_id)
            if curr_time is not None and prev_time is not None:
                dt = max(1e-3, curr_time - prev_time)
            else:
                dt = 1 / 25.0
            motion_level = self.calculate_motion(person_box, prev_box, dt)
            self.prev_boxes[track_id] = person_box
            if curr_time is not None:
                self.prev_times[track_id] = curr_time
        else:
            motion_level = 0.0

        # تصنيف فوري
        result = self.classify_activity(pose_info, objects_info, motion_level)

        # تنعيم زمني لكل track
        if track_id is not None:
            hist = self.histories.setdefault(track_id, deque(maxlen=self.window_size))
            hist.append(result)
            # تجميع عبر النوافذ: اختيار النشاط الأكثر تكراراً، ومتوسط الثقة لهذا النشاط
            most_common = Counter([r.activity for r in hist]).most_common(1)[0][0]
            confs = [r.confidence for r in hist if r.activity == most_common]
            smoothed = ActivityResult(activity=most_common, confidence=float(np.mean(confs) if confs else result.confidence), details=result.details)
            return smoothed
        else:
            return result
