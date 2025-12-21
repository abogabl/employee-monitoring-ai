"""
مُقيِّم جودة الصور التدريبية
Quality Assessor for Training Images
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

import cv2
import numpy as np

from .models import QualityMetrics

logger = logging.getLogger(__name__)


class QualityAssessor:
    """مُقيِّم جودة الصور"""
    
    def __init__(
        self,
        min_sharpness: float = 50.0,
        min_brightness: float = 60.0,
        max_brightness: float = 200.0,
        min_face_size: int = 80,
        max_face_angle: float = 30.0
    ):
        """تهيئة المُقيِّم
        
        Args:
            min_sharpness: الحد الأدنى للوضوح
            min_brightness: الحد الأدنى للإضاءة
            max_brightness: الحد الأقصى للإضاءة
            min_face_size: الحد الأدنى لحجم الوجه (بكسل)
            max_face_angle: الحد الأقصى لزاوية الوجه (درجة)
        """
        self.min_sharpness = min_sharpness
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.min_face_size = min_face_size
        self.max_face_angle = max_face_angle
        
        logger.info("✓ تم تهيئة مُقيِّم الجودة")
    
    def assess_image(
        self,
        image: np.ndarray,
        bbox: Optional[tuple] = None
    ) -> QualityMetrics:
        """تقييم جودة صورة
        
        Args:
            image: الصورة (NumPy array)
            bbox: صندوق الحدود للوجه (x1, y1, x2, y2) اختياري
            
        Returns:
            مقاييس الجودة
        """
        # قياس الوضوح
        sharpness = self._measure_sharpness(image)
        
        # قياس الإضاءة
        brightness = self._measure_brightness(image)
        
        # قياس حجم الوجه
        face_size = self._measure_face_size(image, bbox)
        
        # قياس زاوية الوجه (تقديري)
        face_angle = self._estimate_face_angle(image, bbox)
        
        # حساب الدرجة الكلية
        overall_score = self._calculate_overall_score(
            sharpness, brightness, face_size, face_angle
        )
        
        metrics = QualityMetrics(
            sharpness=sharpness,
            brightness=brightness,
            face_size=face_size,
            face_angle=face_angle,
            overall_score=overall_score
        )
        
        return metrics
    
    def is_acceptable(self, metrics: QualityMetrics) -> bool:
        """هل الصورة مقبولة؟
        
        Args:
            metrics: مقاييس الجودة
            
        Returns:
            True إذا كانت مقبولة
        """
        checks = [
            metrics.sharpness >= self.min_sharpness,
            self.min_brightness <= metrics.brightness <= self.max_brightness,
            metrics.face_size >= self.min_face_size,
            metrics.face_angle <= self.max_face_angle,
            metrics.overall_score >= 0.6,  # 60% كحد أدنى
        ]
        
        return all(checks)
    
    def get_rejection_reasons(self, metrics: QualityMetrics) -> list[str]:
        """الحصول على أسباب الرفض
        
        Args:
            metrics: مقاييس الجودة
            
        Returns:
            قائمة الأسباب
        """
        reasons = []
        
        if metrics.sharpness < self.min_sharpness:
            reasons.append(f"وضوح منخفض ({metrics.sharpness:.1f} < {self.min_sharpness})")
        
        if metrics.brightness < self.min_brightness:
            reasons.append(f"إضاءة منخفضة ({metrics.brightness:.1f} < {self.min_brightness})")
        elif metrics.brightness > self.max_brightness:
            reasons.append(f"إضاءة عالية ({metrics.brightness:.1f} > {self.max_brightness})")
        
        if metrics.face_size < self.min_face_size:
            reasons.append(f"وجه صغير ({metrics.face_size}px < {self.min_face_size}px)")
        
        if metrics.face_angle > self.max_face_angle:
            reasons.append(f"زاوية كبيرة ({metrics.face_angle:.1f}° > {self.max_face_angle}°)")
        
        if metrics.overall_score < 0.6:
            reasons.append(f"درجة إجمالية منخفضة ({metrics.overall_score:.1%})")
        
        return reasons
    
    # ==================== دوال القياس ====================
    
    def _measure_sharpness(self, image: np.ndarray) -> float:
        """قياس وضوح الصورة باستخدام Laplacian
        
        Args:
            image: الصورة
            
        Returns:
            درجة الوضوح (أعلى = أفضل)
        """
        try:
            # تحويل لرمادي إذا لزم الأمر
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # حساب Laplacian variance
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            sharpness = laplacian.var()
            
            return float(sharpness)
            
        except Exception as e:
            logger.warning(f"خطأ في قياس الوضوح: {e}")
            return 0.0
    
    def _measure_brightness(self, image: np.ndarray) -> float:
        """قياس الإضاءة
        
        Args:
            image: الصورة
            
        Returns:
            متوسط الإضاءة (0-255)
        """
        try:
            # تحويل لرمادي
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # متوسط القيم
            brightness = np.mean(gray)
            
            return float(brightness)
            
        except Exception as e:
            logger.warning(f"خطأ في قياس الإضاءة: {e}")
            return 0.0
    
    def _measure_face_size(
        self,
        image: np.ndarray,
        bbox: Optional[tuple]
    ) -> int:
        """قياس حجم الوجه
        
        Args:
            image: الصورة
            bbox: صندوق الحدود (x1, y1, x2, y2)
            
        Returns:
            متوسط العرض والارتفاع بالبكسل
        """
        try:
            if bbox is None:
                # إذا لم يكن هناك bbox، استخدم حجم الصورة
                h, w = image.shape[:2]
                return min(h, w)
            
            x1, y1, x2, y2 = bbox
            width = x2 - x1
            height = y2 - y1
            
            # متوسط العرض والارتفاع
            avg_size = int((width + height) / 2)
            
            return avg_size
            
        except Exception as e:
            logger.warning(f"خطأ في قياس حجم الوجه: {e}")
            return 0
    
    def _estimate_face_angle(
        self,
        image: np.ndarray,
        bbox: Optional[tuple]
    ) -> float:
        """تقدير زاوية الوجه (تقديري بسيط)
        
        Args:
            image: الصورة
            bbox: صندوق الحدود
            
        Returns:
            الزاوية المقدرة بالدرجات
        """
        try:
            # طريقة بسيطة: قياس التماثل الأفقي
            # الوجه المستقيم يكون أكثر تماثلاً
            
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            h, w = gray.shape
            
            # قسم الصورة لنصفين
            left_half = gray[:, :w//2]
            right_half = gray[:, w//2:]
            
            # اعكس النصف الأيمن
            right_flipped = cv2.flip(right_half, 1)
            
            # احسب الفرق
            if left_half.shape != right_flipped.shape:
                # قص للحجم الأصغر
                min_w = min(left_half.shape[1], right_flipped.shape[1])
                left_half = left_half[:, :min_w]
                right_flipped = right_flipped[:, :min_w]
            
            diff = cv2.absdiff(left_half, right_flipped)
            asymmetry = np.mean(diff)
            
            # تحويل لزاوية تقديرية (0-45 درجة)
            # asymmetry عالي = زاوية عالية
            estimated_angle = min(45.0, asymmetry / 2.0)
            
            return float(estimated_angle)
            
        except Exception as e:
            logger.warning(f"خطأ في تقدير زاوية الوجه: {e}")
            return 0.0
    
    def _calculate_overall_score(
        self,
        sharpness: float,
        brightness: float,
        face_size: int,
        face_angle: float
    ) -> float:
        """حساب الدرجة الإجمالية
        
        Args:
            sharpness: الوضوح
            brightness: الإضاءة
            face_size: حجم الوجه
            face_angle: زاوية الوجه
            
        Returns:
            الدرجة (0.0 - 1.0)
        """
        # تطبيع كل قيمة لنطاق 0-1
        
        # الوضوح: 0-200 → 0-1
        sharpness_norm = min(1.0, sharpness / 200.0)
        
        # الإضاءة: أفضل قيمة حول 130
        brightness_diff = abs(brightness - 130.0)
        brightness_norm = max(0.0, 1.0 - (brightness_diff / 130.0))
        
        # حجم الوجه: 0-200 → 0-1
        face_size_norm = min(1.0, face_size / 200.0)
        
        # الزاوية: 0-45 → 1-0 (معكوس)
        face_angle_norm = max(0.0, 1.0 - (face_angle / 45.0))
        
        # حساب المتوسط المرجح
        weights = {
            'sharpness': 0.30,
            'brightness': 0.25,
            'face_size': 0.25,
            'face_angle': 0.20,
        }
        
        overall = (
            sharpness_norm * weights['sharpness'] +
            brightness_norm * weights['brightness'] +
            face_size_norm * weights['face_size'] +
            face_angle_norm * weights['face_angle']
        )
        
        return round(overall, 3)
