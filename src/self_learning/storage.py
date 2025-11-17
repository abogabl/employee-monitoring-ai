"""
نظام تخزين الصور التدريبية
Storage System for Training Images
"""
from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class ImageStorage:
    """نظام تخزين الصور التدريبية المنظم"""
    
    def __init__(self, base_path: str | Path = "training_data"):
        """تهيئة نظام التخزين
        
        Args:
            base_path: المسار الأساسي لحفظ الصور
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # المجلدات الفرعية
        self.raw_path = self.base_path / "raw"  # الصور الخام
        self.validated_path = self.base_path / "validated"  # الصور المؤكدة
        self.rejected_path = self.base_path / "rejected"  # الصور المرفوضة
        
        for path in [self.raw_path, self.validated_path, self.rejected_path]:
            path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"✓ تم تهيئة نظام التخزين: {self.base_path}")
    
    def save_image(
        self,
        image: np.ndarray,
        employee_id: str,
        timestamp: Optional[datetime] = None,
        category: str = "raw",
        metadata: Optional[dict] = None
    ) -> Path:
        """حفظ صورة
        
        Args:
            image: الصورة (NumPy array)
            employee_id: معرف الموظف
            timestamp: وقت الالتقاط (اختياري)
            category: الفئة (raw/validated/rejected)
            metadata: بيانات إضافية (اختياري)
            
        Returns:
            مسار الصورة المحفوظة
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # اختيار المجلد المناسب
        if category == "validated":
            target_dir = self.validated_path / employee_id
        elif category == "rejected":
            target_dir = self.rejected_path / employee_id
        else:
            target_dir = self.raw_path / employee_id
        
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # تسمية الملف: EMP001_20231117_120530_123.jpg
        filename = self._generate_filename(employee_id, timestamp)
        file_path = target_dir / filename
        
        # حفظ الصورة
        success = cv2.imwrite(str(file_path), image)
        
        if success:
            logger.debug(f"✓ تم حفظ الصورة: {file_path}")
            return file_path
        else:
            logger.error(f"✗ فشل حفظ الصورة: {file_path}")
            raise IOError(f"فشل حفظ الصورة: {file_path}")
    
    def save_face_crop(
        self,
        frame: np.ndarray,
        bbox: tuple,
        employee_id: str,
        timestamp: Optional[datetime] = None,
        category: str = "raw",
        padding: int = 20
    ) -> Optional[Path]:
        """حفظ قص الوجه من الإطار
        
        Args:
            frame: الإطار الكامل
            bbox: صندوق الحدود (x1, y1, x2, y2)
            employee_id: معرف الموظف
            timestamp: وقت الالتقاط
            category: الفئة
            padding: هامش حول الوجه (بكسل)
            
        Returns:
            مسار الصورة أو None عند الفشل
        """
        try:
            x1, y1, x2, y2 = bbox
            
            # إضافة هامش
            h, w = frame.shape[:2]
            x1 = max(0, int(x1 - padding))
            y1 = max(0, int(y1 - padding))
            x2 = min(w, int(x2 + padding))
            y2 = min(h, int(y2 + padding))
            
            # قص الوجه
            face_crop = frame[y1:y2, x1:x2]
            
            if face_crop.size == 0:
                logger.warning("الوجه المقصوص فارغ")
                return None
            
            # حفظ
            return self.save_image(face_crop, employee_id, timestamp, category)
            
        except Exception as e:
            logger.error(f"خطأ في قص وحفظ الوجه: {e}")
            return None
    
    def move_image(
        self,
        source_path: Path,
        new_category: str,
        employee_id: Optional[str] = None
    ) -> Path:
        """نقل صورة بين الفئات
        
        Args:
            source_path: مسار الصورة الحالي
            new_category: الفئة الجديدة (validated/rejected/raw)
            employee_id: معرف الموظف (اختياري، سيُستخرج من المسار)
            
        Returns:
            المسار الجديد
        """
        if not source_path.exists():
            raise FileNotFoundError(f"الصورة غير موجودة: {source_path}")
        
        # استخراج معرف الموظف من المسار
        if employee_id is None:
            employee_id = source_path.parent.name
        
        # تحديد المجلد الجديد
        if new_category == "validated":
            target_dir = self.validated_path / employee_id
        elif new_category == "rejected":
            target_dir = self.rejected_path / employee_id
        else:
            target_dir = self.raw_path / employee_id
        
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # المسار الجديد
        new_path = target_dir / source_path.name
        
        # نقل الملف
        shutil.move(str(source_path), str(new_path))
        logger.info(f"✓ تم نقل الصورة: {source_path.name} → {new_category}")
        
        return new_path
    
    def get_employee_images(
        self,
        employee_id: str,
        category: str = "raw",
        limit: Optional[int] = None
    ) -> list[Path]:
        """الحصول على صور موظف
        
        Args:
            employee_id: معرف الموظف
            category: الفئة
            limit: الحد الأقصى
            
        Returns:
            قائمة مسارات الصور
        """
        if category == "validated":
            emp_dir = self.validated_path / employee_id
        elif category == "rejected":
            emp_dir = self.rejected_path / employee_id
        else:
            emp_dir = self.raw_path / employee_id
        
        if not emp_dir.exists():
            return []
        
        # جمع كل الصور
        images = sorted(emp_dir.glob("*.jpg"), reverse=True)
        
        if limit:
            images = images[:limit]
        
        return images
    
    def count_images(
        self,
        employee_id: Optional[str] = None,
        category: str = "raw"
    ) -> int:
        """عد الصور
        
        Args:
            employee_id: معرف الموظف (None = الكل)
            category: الفئة
            
        Returns:
            عدد الصور
        """
        if employee_id:
            images = self.get_employee_images(employee_id, category)
            return len(images)
        else:
            # عد كل الصور في الفئة
            if category == "validated":
                base_dir = self.validated_path
            elif category == "rejected":
                base_dir = self.rejected_path
            else:
                base_dir = self.raw_path
            
            return len(list(base_dir.glob("**/*.jpg")))
    
    def get_storage_stats(self) -> dict:
        """إحصائيات التخزين
        
        Returns:
            قاموس الإحصائيات
        """
        stats = {
            'raw_images': self.count_images(category='raw'),
            'validated_images': self.count_images(category='validated'),
            'rejected_images': self.count_images(category='rejected'),
            'total_employees': len(list(self.raw_path.iterdir())),
            'storage_size_mb': self._calculate_size(self.base_path),
        }
        return stats
    
    def cleanup_old_images(
        self,
        days: int = 90,
        category: str = "rejected"
    ) -> int:
        """حذف الصور القديمة
        
        Args:
            days: عدد الأيام
            category: الفئة المراد تنظيفها
            
        Returns:
            عدد الصور المحذوفة
        """
        if category == "validated":
            base_dir = self.validated_path
        elif category == "rejected":
            base_dir = self.rejected_path
        else:
            base_dir = self.raw_path
        
        cutoff = datetime.now().timestamp() - (days * 24 * 3600)
        deleted = 0
        
        for img_path in base_dir.glob("**/*.jpg"):
            if img_path.stat().st_mtime < cutoff:
                img_path.unlink()
                deleted += 1
        
        logger.info(f"✓ تم حذف {deleted} صورة قديمة من {category}")
        return deleted
    
    def _generate_filename(
        self,
        employee_id: str,
        timestamp: datetime
    ) -> str:
        """توليد اسم ملف منظم
        
        Args:
            employee_id: معرف الموظف
            timestamp: الوقت
            
        Returns:
            اسم الملف
        """
        # EMP001_20231117_120530_123.jpg
        date_str = timestamp.strftime("%Y%m%d")
        time_str = timestamp.strftime("%H%M%S")
        ms_str = str(timestamp.microsecond)[:3]
        
        return f"{employee_id}_{date_str}_{time_str}_{ms_str}.jpg"
    
    def _calculate_size(self, path: Path) -> float:
        """حساب حجم المجلد بالميجابايت
        
        Args:
            path: مسار المجلد
            
        Returns:
            الحجم بالميجابايت
        """
        total_size = 0
        for file_path in path.glob("**/*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        
        return round(total_size / (1024 * 1024), 2)
