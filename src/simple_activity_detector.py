"""
كاشف نشاط بسيط ومباشر بدون MediaPipe
يعتمد فقط على كشف الأشياء من YOLO والحركة البسيطة
"""
from __future__ import annotations
import logging
import math
from typing import Dict, List, Any, Tuple, Optional
from collections import deque
import numpy as np

logger = logging.getLogger(__name__)

# أسماء الأشياء المهمة
LAPTOP_CLASSES = [63]  # laptop
KEYBOARD_CLASSES = [66]  # keyboard
MONITOR_CLASSES = [62, 72]  # tv, monitor
PHONE_CLASSES = [67]  # cell phone

COMPUTER_CLASSES = LAPTOP_CLASSES + KEYBOARD_CLASSES + MONITOR_CLASSES

COCO_NAMES = {
    62: 'tv',
    63: 'laptop',
    66: 'keyboard',
    67: 'cell phone',
    72: 'monitor'
}


class SimpleActivityDetector:
    """كاشف نشاط بسيط ومباشر"""
    
    def __init__(self, max_distance: int = 300, motion_window: int = 5, smoothing_method: str = 'ema'):
        """
        Args:
            max_distance: المسافة القصوى (بالبيكسل) لاعتبار الشيء قريباً من الشخص
            motion_window: عدد الإطارات لحساب متوسط الحركة (للـ SMA)
            smoothing_method: طريقة التنعيم - 'sma' (Simple Moving Average) أو 'ema' (Exponential Moving Average) أو 'none'
        """
        self.max_distance = max_distance
        self.motion_window = motion_window
        self.smoothing_method = smoothing_method.lower()
        self.prev_boxes = {}  # لحساب الحركة
        self.motion_history = {}  # تاريخ الحركة لكل track (للـ SMA)
        self.ema_motion = {}  # EMA للحركة (للـ EMA)
        
        logger.info(f"✓ تم تهيئة Motion Smoothing: method={self.smoothing_method}, window={self.motion_window}")
        
    def detect_activity(
        self,
        person_box: Tuple[int, int, int, int],
        track_id: int,
        yolo_detections: List[Dict[str, Any]],
        frame_time: float
    ) -> Tuple[str, float]:
        """
        كشف النشاط بناءً على الأشياء القريبة والحركة
        
        Returns:
            (activity_name, confidence)
        """
        x1, y1, x2, y2 = person_box
        person_center = ((x1 + x2) / 2, (y1 + y2) / 2)
        
        # 1. البحث عن الأشياء القريبة
        computer_nearby = False
        phone_nearby = False
        min_computer_dist = float('inf')
        min_phone_dist = float('inf')
        
        for det in yolo_detections:
            cls_id = int(det.get('class', -1))
            box = det.get('box', None) or det.get('bbox', None)
            if box is None:
                continue
            
            # حساب المسافة من مركز الشخص
            if len(box) == 4:
                obj_center = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
                distance = math.sqrt(
                    (person_center[0] - obj_center[0])**2 + 
                    (person_center[1] - obj_center[1])**2
                )
                
                if distance <= self.max_distance:
                    if cls_id in COMPUTER_CLASSES:
                        computer_nearby = True
                        min_computer_dist = min(min_computer_dist, distance)
                    elif cls_id in PHONE_CLASSES:
                        phone_nearby = True
                        min_phone_dist = min(min_phone_dist, distance)
        
        # 2. حساب الحركة (مع smoothing)
        motion_level = self._calculate_motion_smoothed(track_id, person_box, frame_time)
        
        # 3. تطبيق القواعد البسيطة المحسّنة
        # القاعدة 1: إذا كان هناك كمبيوتر قريب → working (الأولوية الأعلى)
        if computer_nearby:
            confidence = 0.9 if min_computer_dist < 200 else 0.75
            return 'working', confidence
        
        # القاعدة 2: إذا كان هناك هاتف قريب → on_phone
        if phone_nearby:
            confidence = 0.85 if min_phone_dist < 150 else 0.7
            return 'on_phone', confidence
        
        # القاعدة 3: إذا الحركة قليلة جداً → sleeping (threshold محسّن)
        # فقط للحركة الشبه معدومة تماماً
        if motion_level < 0.002:
            return 'sleeping', 0.85
        
        # القاعدة 4: حركة قليلة جداً → idle (بين النوم والعمل)
        # مثل: جالس يفكر، يقرأ بدون حركة كثيرة
        if motion_level < 0.015:
            return 'idle', 0.7
        
        # القاعدة 5: حركة معقولة أو أكثر → working (default)
        # في بيئة العمل، الافتراض الأساسي هو العمل
        if motion_level < 0.2:
            return 'working', 0.75
        
        # حركة كبيرة جداً → working بثقة عالية
        return 'working', 0.9
    
    def _calculate_motion(
        self, 
        track_id: int, 
        current_box: Tuple[int, int, int, int],
        frame_time: float
    ) -> float:
        """
        حساب مستوى الحركة (0..1) بناءً على تغير الموضع
        
        Returns:
            motion_level: 0 = لا حركة, 1 = حركة كبيرة
        """
        if track_id not in self.prev_boxes:
            self.prev_boxes[track_id] = {
                'box': current_box,
                'time': frame_time
            }
            return 0.0
        
        prev_data = self.prev_boxes[track_id]
        prev_box = prev_data['box']
        prev_time = prev_data['time']
        
        # حساب إزاحة المركز
        curr_center = np.array([(current_box[0] + current_box[2]) / 2, 
                                (current_box[1] + current_box[3]) / 2])
        prev_center = np.array([(prev_box[0] + prev_box[2]) / 2, 
                                (prev_box[1] + prev_box[3]) / 2])
        
        displacement = np.linalg.norm(curr_center - prev_center)
        
        # حساب قطر الصندوق للتطبيع
        width = current_box[2] - current_box[0]
        height = current_box[3] - current_box[1]
        diagonal = math.sqrt(width**2 + height**2)
        
        # حساب السرعة النسبية
        time_delta = max(frame_time - prev_time, 0.001)
        normalized_speed = (displacement / diagonal) / time_delta
        
        # تحديث
        self.prev_boxes[track_id] = {
            'box': current_box,
            'time': frame_time
        }
        
        # قص القيمة بين 0 و 1
        motion_level = min(normalized_speed, 1.0)
        
        return motion_level
    
    def _calculate_motion_smoothed(
        self,
        track_id: int,
        current_box: Tuple[int, int, int, int],
        frame_time: float
    ) -> float:
        """
        حساب مستوى الحركة مع التنعيم (Smoothing)
        
        Returns:
            smoothed_motion_level: مستوى الحركة المنعّم
        """
        # حساب الحركة الخام (raw motion)
        raw_motion = self._calculate_motion(track_id, current_box, frame_time)
        
        # تطبيق التنعيم حسب الطريقة المختارة
        if self.smoothing_method == 'sma':
            # Simple Moving Average
            return self._apply_sma(track_id, raw_motion)
        elif self.smoothing_method == 'ema':
            # Exponential Moving Average
            return self._apply_ema(track_id, raw_motion)
        else:
            # بدون تنعيم
            return raw_motion
    
    def _apply_sma(self, track_id: int, raw_motion: float) -> float:
        """
        تطبيق Simple Moving Average على الحركة
        
        Args:
            track_id: معرف المسار
            raw_motion: مستوى الحركة الخام
        
        Returns:
            smoothed_motion: متوسط الحركة لآخر N إطارات
        """
        # إنشاء buffer إذا لم يكن موجوداً
        if track_id not in self.motion_history:
            self.motion_history[track_id] = deque(maxlen=self.motion_window)
        
        # إضافة الحركة الحالية
        self.motion_history[track_id].append(raw_motion)
        
        # حساب المتوسط
        if len(self.motion_history[track_id]) > 0:
            smoothed_motion = np.mean(list(self.motion_history[track_id]))
        else:
            smoothed_motion = raw_motion
        
        return smoothed_motion
    
    def _apply_ema(self, track_id: int, raw_motion: float, alpha: float = 0.3) -> float:
        """
        تطبيق Exponential Moving Average على الحركة
        
        Args:
            track_id: معرف المسار
            raw_motion: مستوى الحركة الخام
            alpha: معامل التنعيم (0-1)
                  - alpha قريب من 0: تنعيم أكثر، استجابة أبطأ
                  - alpha قريب من 1: تنعيم أقل، استجابة أسرع
        
        Returns:
            ema_motion: EMA للحركة
        """
        # تهيئة EMA إذا لم يكن موجوداً
        if track_id not in self.ema_motion:
            self.ema_motion[track_id] = raw_motion
        else:
            # EMA = alpha × current + (1-alpha) × previous_EMA
            self.ema_motion[track_id] = (alpha * raw_motion + 
                                         (1 - alpha) * self.ema_motion[track_id])
        
        return self.ema_motion[track_id]
