"""
مُجمِّع البيانات التلقائي
Automatic Data Collector for Self-Learning
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import numpy as np

from .database import SelfLearningDB
from .models import TrainingImage
from .quality_assessor import QualityAssessor
from .storage import ImageStorage

logger = logging.getLogger(__name__)


class DataCollector:
    """مُجمِّع البيانات التلقائي"""
    
    def __init__(
        self,
        db: Optional[SelfLearningDB] = None,
        storage: Optional[ImageStorage] = None,
        quality_assessor: Optional[QualityAssessor] = None,
        max_images_per_day: int = 20,
        min_confidence: float = 0.80,
        auto_add_to_queue: bool = True
    ):
        """تهيئة المُجمِّع
        
        Args:
            db: قاعدة البيانات
            storage: نظام التخزين
            quality_assessor: مُقيِّم الجودة
            max_images_per_day: الحد الأقصى للصور/يوم لكل موظف
            min_confidence: الحد الأدنى لثقة التعرف
            auto_add_to_queue: إضافة تلقائية لقائمة التأكيد
        """
        self.db = db or SelfLearningDB()
        self.storage = storage or ImageStorage()
        self.quality_assessor = quality_assessor or QualityAssessor()
        
        self.max_images_per_day = max_images_per_day
        self.min_confidence = min_confidence
        self.auto_add_to_queue = auto_add_to_queue
        
        # إحصائيات الجلسة
        self.session_stats = {
            'collected': 0,
            'rejected_quality': 0,
            'rejected_quota': 0,
            'rejected_confidence': 0,
        }
        
        logger.info("✓ تم تهيئة مُجمِّع البيانات")
    
    def collect_face(
        self,
        frame: np.ndarray,
        employee_id: str,
        confidence: float,
        bbox: tuple,
        predictions: Optional[list] = None,
        metadata: Optional[dict] = None
    ) -> Optional[int]:
        """جمع وجه جديد
        
        Args:
            frame: الإطار الكامل
            employee_id: معرف الموظف المتوقع
            confidence: ثقة التعرف
            bbox: صندوق الحدود (x1, y1, x2, y2)
            predictions: أفضل التوقعات (للتعلم النشط)
            metadata: بيانات إضافية
            
        Returns:
            معرف الصورة في قاعدة البيانات أو None
        """
        try:
            # 1. التحقق من الثقة
            if confidence < self.min_confidence:
                logger.debug(f"ثقة منخفضة ({confidence:.2%}) للموظف {employee_id}")
                self.session_stats['rejected_confidence'] += 1
                return None
            
            # 2. التحقق من الحصة اليومية
            today_count = self.db.count_employee_images_today(employee_id)
            if today_count >= self.max_images_per_day:
                logger.debug(f"وصل الموظف {employee_id} للحد الأقصى اليومي ({today_count}/{self.max_images_per_day})")
                self.session_stats['rejected_quota'] += 1
                return None
            
            # 3. قص الوجه
            x1, y1, x2, y2 = bbox
            h, w = frame.shape[:2]
            
            # إضافة هامش
            padding = 20
            x1 = max(0, int(x1 - padding))
            y1 = max(0, int(y1 - padding))
            x2 = min(w, int(x2 + padding))
            y2 = min(h, int(y2 + padding))
            
            face_crop = frame[y1:y2, x1:x2]
            
            if face_crop.size == 0:
                logger.warning("الوجه المقصوص فارغ")
                return None
            
            # 4. تقييم الجودة
            quality_metrics = self.quality_assessor.assess_image(face_crop, bbox)
            
            if not self.quality_assessor.is_acceptable(quality_metrics):
                reasons = self.quality_assessor.get_rejection_reasons(quality_metrics)
                logger.debug(f"جودة منخفضة للموظف {employee_id}: {', '.join(reasons)}")
                self.session_stats['rejected_quality'] += 1
                return None
            
            # 5. حفظ الصورة
            timestamp = datetime.now()
            image_path = self.storage.save_image(
                image=face_crop,
                employee_id=employee_id,
                timestamp=timestamp,
                category='raw',
                metadata=metadata
            )
            
            # 6. حفظ في قاعدة البيانات
            training_image = TrainingImage(
                employee_id=employee_id,
                image_path=str(image_path),
                capture_timestamp=timestamp,
                confidence=confidence,
                quality_score=quality_metrics.overall_score,
                quality_details=quality_metrics,
                metadata=metadata or {},
                validated=False,
                used_in_training=False
            )
            
            image_id = self.db.insert_training_image(training_image)
            
            # 7. إضافة لقائمة التأكيد (للحالات المشكوك فيها)
            if self.auto_add_to_queue and self._should_add_to_queue(confidence, predictions):
                priority = self._calculate_priority(confidence, quality_metrics.overall_score)
                self.db.add_to_confirmation_queue(
                    image_id=image_id,
                    top_predictions=predictions or [],
                    priority=priority
                )
                logger.debug(f"تم إضافة للقائمة: صورة {image_id}, أولوية {priority}")
            
            # 8. تحديث الإحصائيات
            self.session_stats['collected'] += 1
            
            logger.info(f"✓ تم جمع صورة للموظف {employee_id}: {image_id} (جودة {quality_metrics.overall_score:.1%})")
            
            return image_id
            
        except Exception as e:
            logger.error(f"خطأ في جمع الوجه: {e}")
            return None
    
    def _should_add_to_queue(
        self,
        confidence: float,
        predictions: Optional[list]
    ) -> bool:
        """هل يجب إضافة الصورة لقائمة التأكيد؟
        
        Args:
            confidence: الثقة
            predictions: أفضل التوقعات
            
        Returns:
            True إذا كانت تحتاج تأكيد بشري
        """
        # إضافة للقائمة إذا:
        # 1. الثقة بين 0.70 - 0.85 (منطقة رمادية)
        if 0.70 <= confidence <= 0.85:
            return True
        
        # 2. هناك توقع آخر قريب
        if predictions and len(predictions) >= 2:
            top1_conf = predictions[0].get('confidence', 0)
            top2_conf = predictions[1].get('confidence', 0)
            
            # إذا كان الفرق أقل من 0.15
            if top1_conf - top2_conf < 0.15:
                return True
        
        return False
    
    def _calculate_priority(
        self,
        confidence: float,
        quality_score: float
    ) -> int:
        """حساب أولوية التأكيد
        
        Args:
            confidence: الثقة
            quality_score: درجة الجودة
            
        Returns:
            الأولوية (1 = عاجل, 10 = منخفض)
        """
        # الأولوية تعتمد على:
        # - ثقة منخفضة = أولوية أعلى
        # - جودة عالية = أولوية أعلى
        
        # حساب النقاط (0-10)
        confidence_factor = (1.0 - confidence) * 5  # 0-5
        quality_factor = quality_score * 5  # 0-5
        
        total_score = confidence_factor + quality_factor
        
        # تحويل لأولوية (1-10)
        # نقاط عالية = أولوية عالية (رقم منخفض)
        priority = max(1, min(10, 11 - int(total_score)))
        
        return priority
    
    def get_session_stats(self) -> dict:
        """الحصول على إحصائيات الجلسة
        
        Returns:
            قاموس الإحصائيات
        """
        total_attempts = sum(self.session_stats.values())
        
        stats = self.session_stats.copy()
        stats['total_attempts'] = total_attempts
        
        if total_attempts > 0:
            stats['success_rate'] = round(
                self.session_stats['collected'] / total_attempts * 100, 1
            )
        else:
            stats['success_rate'] = 0.0
        
        return stats
    
    def reset_session_stats(self) -> None:
        """إعادة تعيين إحصائيات الجلسة"""
        self.session_stats = {
            'collected': 0,
            'rejected_quality': 0,
            'rejected_quota': 0,
            'rejected_confidence': 0,
        }
        logger.debug("تم إعادة تعيين إحصائيات الجلسة")


class CollectionPolicy:
    """سياسة الجمع - متى وكيف نجمع الصور"""
    
    def __init__(
        self,
        min_interval_seconds: int = 300,  # 5 دقائق
        max_images_per_session: int = 3,
        require_different_angles: bool = True
    ):
        """تهيئة السياسة
        
        Args:
            min_interval_seconds: الحد الأدنى بين الصور (ثواني)
            max_images_per_session: الحد الأقصى للصور لكل جلسة حضور
            require_different_angles: طلب زوايا مختلفة
        """
        self.min_interval_seconds = min_interval_seconds
        self.max_images_per_session = max_images_per_session
        self.require_different_angles = require_different_angles
        
        # تتبع آخر جمع لكل موظف
        self.last_collection = {}  # {employee_id: timestamp}
        self.session_count = {}  # {employee_id: count}
    
    def can_collect(
        self,
        employee_id: str,
        current_time: Optional[datetime] = None
    ) -> bool:
        """هل يمكن جمع صورة للموظف؟
        
        Args:
            employee_id: معرف الموظف
            current_time: الوقت الحالي (اختياري)
            
        Returns:
            True إذا كان يمكن الجمع
        """
        if current_time is None:
            current_time = datetime.now()
        
        # التحقق من الفاصل الزمني
        if employee_id in self.last_collection:
            last_time = self.last_collection[employee_id]
            elapsed = (current_time - last_time).total_seconds()
            
            if elapsed < self.min_interval_seconds:
                return False
        
        # التحقق من عدد الصور في الجلسة
        session_count = self.session_count.get(employee_id, 0)
        if session_count >= self.max_images_per_session:
            return False
        
        return True
    
    def mark_collected(
        self,
        employee_id: str,
        current_time: Optional[datetime] = None
    ) -> None:
        """تسجيل أن تم جمع صورة
        
        Args:
            employee_id: معرف الموظف
            current_time: الوقت الحالي
        """
        if current_time is None:
            current_time = datetime.now()
        
        self.last_collection[employee_id] = current_time
        self.session_count[employee_id] = self.session_count.get(employee_id, 0) + 1
    
    def reset_session(self, employee_id: str) -> None:
        """إعادة تعيين جلسة موظف
        
        Args:
            employee_id: معرف الموظف
        """
        if employee_id in self.session_count:
            del self.session_count[employee_id]
        
        if employee_id in self.last_collection:
            del self.last_collection[employee_id]
