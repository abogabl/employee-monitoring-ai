"""
Activity Detector - MediaPipe Pose-based activity recognition
Phase 4 Implementation
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
import cv2

logger = logging.getLogger(__name__)


class ActivityDetector:
    """كاشف الأنشطة باستخدام MediaPipe Pose"""
    
    # تعريف الأنشطة
    ACTIVITIES = {
        'working': 'عمل',
        'sleeping': 'نوم',
        'phone': 'موبايل',
        'idle': 'خمول',
        'walking': 'حركة',
        'unknown': 'غير معروف'
    }
    
    def __init__(
        self,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5
    ):
        """
        تهيئة كاشف الأنشطة
        
        Args:
            min_detection_confidence: عتبة الكشف
            min_tracking_confidence: عتبة التتبع
        """
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        
        # تهيئة MediaPipe
        self._init_pose()
        
        # تاريخ الأنشطة للتنعيم
        self.activity_history: Dict[int, List[str]] = {}
        self.history_size = 5
    
    def _init_pose(self):
        """تهيئة MediaPipe Pose"""
        try:
            import mediapipe as mp
            
            self.mp_pose = mp.solutions.pose
            self.pose = self.mp_pose.Pose(
                static_image_mode=False,
                model_complexity=0,  # أسرع نموذج
                smooth_landmarks=True,
                min_detection_confidence=self.min_detection_confidence,
                min_tracking_confidence=self.min_tracking_confidence
            )
            self.mp_drawing = mp.solutions.drawing_utils
            
            logger.info("✓ تم تحميل MediaPipe Pose")
            self.initialized = True
            
        except ImportError:
            logger.warning("⚠️ MediaPipe غير مثبت - استخدم: pip install mediapipe")
            self.pose = None
            self.initialized = False
        except Exception as e:
            logger.error(f"✗ فشل تحميل MediaPipe: {e}")
            self.pose = None
            self.initialized = False
    
    def detect_activity(
        self,
        frame: np.ndarray,
        person_box: Tuple[int, int, int, int],
        person_id: int
    ) -> Tuple[str, float]:
        """
        كشف نشاط شخص معين
        
        Args:
            frame: الصورة الكاملة
            person_box: (x1, y1, x2, y2) موقع الشخص
            person_id: معرف الشخص
            
        Returns:
            (النشاط, الثقة)
        """
        if not self.initialized or self.pose is None:
            return self._simple_activity_detection(person_box, frame.shape)
        
        x1, y1, x2, y2 = person_box
        
        # التأكد من الحدود
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        if x2 <= x1 or y2 <= y1:
            return ('unknown', 0.0)
        
        try:
            # قص صورة الشخص
            person_crop = frame[y1:y2, x1:x2]
            
            # تحويل BGR إلى RGB
            rgb_crop = cv2.cvtColor(person_crop, cv2.COLOR_BGR2RGB)
            
            # كشف الوضعية
            results = self.pose.process(rgb_crop)
            
            if results.pose_landmarks:
                activity, confidence = self._analyze_pose(results.pose_landmarks)
            else:
                activity, confidence = self._simple_activity_detection(person_box, frame.shape)
            
            # تنعيم النتائج
            activity = self._smooth_activity(person_id, activity)
            
            return (activity, confidence)
            
        except Exception as e:
            logger.debug(f"خطأ في كشف النشاط: {e}")
            return ('unknown', 0.0)
    
    def _analyze_pose(self, landmarks) -> Tuple[str, float]:
        """تحليل الوضعية لتحديد النشاط"""
        
        # الحصول على النقاط المهمة
        lm = landmarks.landmark
        
        # نقاط الجسم
        nose = lm[self.mp_pose.PoseLandmark.NOSE]
        left_shoulder = lm[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = lm[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
        left_wrist = lm[self.mp_pose.PoseLandmark.LEFT_WRIST]
        right_wrist = lm[self.mp_pose.PoseLandmark.RIGHT_WRIST]
        left_hip = lm[self.mp_pose.PoseLandmark.LEFT_HIP]
        right_hip = lm[self.mp_pose.PoseLandmark.RIGHT_HIP]
        
        # حسابات
        shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
        hip_y = (left_hip.y + right_hip.y) / 2
        torso_angle = abs(shoulder_y - hip_y)
        
        # موقع اليد بالنسبة للوجه
        left_hand_near_face = abs(left_wrist.y - nose.y) < 0.15 and abs(left_wrist.x - nose.x) < 0.2
        right_hand_near_face = abs(right_wrist.y - nose.y) < 0.15 and abs(right_wrist.x - nose.x) < 0.2
        
        # موبايل: يد قرب الأذن أو الوجه
        if left_hand_near_face or right_hand_near_face:
            return ('phone', 0.8)
        
        # نوم: الجسم مائل جداً
        if torso_angle < 0.15:  # الجسم شبه أفقي
            return ('sleeping', 0.7)
        
        # عمل: الشخص منتصب
        if torso_angle > 0.3:
            left_hand_low = left_wrist.y > shoulder_y
            right_hand_low = right_wrist.y > shoulder_y
            if left_hand_low and right_hand_low:
                return ('working', 0.7)
        
        # خمول: افتراضي
        return ('idle', 0.5)
    
    def _simple_activity_detection(
        self,
        person_box: Tuple[int, int, int, int],
        frame_shape: Tuple[int, ...]
    ) -> Tuple[str, float]:
        """كشف نشاط بسيط بدون pose (fallback)"""
        x1, y1, x2, y2 = person_box
        h, w = frame_shape[:2]
        
        # نسبة مساحة الشخص
        person_area = (x2 - x1) * (y2 - y1)
        frame_area = h * w
        area_ratio = person_area / frame_area
        
        # نسبة العرض للارتفاع
        aspect_ratio = (x2 - x1) / max(1, (y2 - y1))
        
        # نائم: الجسم عرضه أكبر من ارتفاعه
        if aspect_ratio > 1.5:
            return ('sleeping', 0.6)
        
        # جالس أو واقف (عمل)
        if aspect_ratio < 0.7:
            return ('working', 0.5)
        
        return ('idle', 0.4)
    
    def _smooth_activity(self, person_id: int, activity: str) -> str:
        """تنعيم النشاط باستخدام التاريخ"""
        if person_id not in self.activity_history:
            self.activity_history[person_id] = []
        
        history = self.activity_history[person_id]
        history.append(activity)
        
        # الاحتفاظ بآخر N قيم فقط
        if len(history) > self.history_size:
            history.pop(0)
        
        # اختيار النشاط الأكثر تكراراً
        if len(history) >= 3:
            from collections import Counter
            most_common = Counter(history).most_common(1)[0][0]
            return most_common
        
        return activity
    
    def get_activity_arabic(self, activity: str) -> str:
        """الحصول على اسم النشاط بالعربية"""
        return self.ACTIVITIES.get(activity, 'غير معروف')
    
    def reset_history(self, person_id: Optional[int] = None):
        """إعادة تعيين تاريخ الأنشطة"""
        if person_id is not None:
            if person_id in self.activity_history:
                del self.activity_history[person_id]
        else:
            self.activity_history = {}
