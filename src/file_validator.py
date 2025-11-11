# -*- coding: utf-8 -*-
"""
File Validator - التحقق من صحة الملفات المرفوعة
يتحقق من:
1. نوع الملف (فيديو فقط)
2. حجم الملف (حد أقصى)
3. صحة الفيديو (يمكن فتحه)
4. مدة الفيديو (حد أقصى)
"""
from __future__ import annotations
import logging
import os
from pathlib import Path
from typing import Tuple, Optional
import cv2

logger = logging.getLogger(__name__)

# الإعدادات الافتراضية
ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}
MAX_FILE_SIZE_MB = 500  # 500 ميجابايت
MAX_VIDEO_DURATION_SECONDS = 600  # 10 دقائق
MIN_VIDEO_DURATION_SECONDS = 1  # ثانية واحدة على الأقل


class FileValidator:
    """التحقق من صحة الملفات المرفوعة"""
    
    def __init__(
        self,
        max_size_mb: int = MAX_FILE_SIZE_MB,
        max_duration_sec: int = MAX_VIDEO_DURATION_SECONDS,
        allowed_extensions: set = None
    ):
        """
        Args:
            max_size_mb: الحد الأقصى لحجم الملف (ميجابايت)
            max_duration_sec: الحد الأقصى لمدة الفيديو (ثواني)
            allowed_extensions: الامتدادات المسموحة
        """
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_duration = max_duration_sec
        self.allowed_extensions = allowed_extensions or ALLOWED_VIDEO_EXTENSIONS
    
    def validate_video_file(self, file_path: str | Path) -> Tuple[bool, Optional[str], Optional[dict]]:
        """
        التحقق من صحة ملف الفيديو
        
        Args:
            file_path: مسار الملف
        
        Returns:
            (is_valid, error_message, video_info)
            - is_valid: True إذا كان الملف صحيح
            - error_message: رسالة الخطأ (None إذا كان صحيح)
            - video_info: معلومات الفيديو (None إذا كان غير صحيح)
        """
        file_path = Path(file_path)
        
        # 1. التحقق من وجود الملف
        if not file_path.exists():
            return False, "الملف غير موجود", None
        
        # 2. التحقق من الامتداد
        extension = file_path.suffix.lower()
        if extension not in self.allowed_extensions:
            return False, f"نوع الملف غير مدعوم. الأنواع المدعومة: {', '.join(self.allowed_extensions)}", None
        
        # 3. التحقق من حجم الملف
        file_size = file_path.stat().st_size
        if file_size > self.max_size_bytes:
            size_mb = file_size / (1024 * 1024)
            max_mb = self.max_size_bytes / (1024 * 1024)
            return False, f"حجم الملف كبير جداً ({size_mb:.1f}MB). الحد الأقصى: {max_mb:.0f}MB", None
        
        if file_size < 1024:  # أقل من 1KB
            return False, "الملف صغير جداً أو تالف", None
        
        # 4. فتح الفيديو والتحقق من صحته
        try:
            cap = cv2.VideoCapture(str(file_path))
            
            if not cap.isOpened():
                return False, "فشل فتح الفيديو. الملف قد يكون تالفاً", None
            
            # الحصول على معلومات الفيديو
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # التحقق من صحة البيانات
            if fps <= 0 or frame_count <= 0 or width <= 0 or height <= 0:
                cap.release()
                return False, "بيانات الفيديو غير صحيحة", None
            
            duration = frame_count / fps
            
            # 5. التحقق من المدة
            if duration < MIN_VIDEO_DURATION_SECONDS:
                cap.release()
                return False, f"الفيديو قصير جداً ({duration:.1f}s). الحد الأدنى: {MIN_VIDEO_DURATION_SECONDS}s", None
            
            if duration > self.max_duration:
                cap.release()
                return False, f"الفيديو طويل جداً ({duration:.1f}s). الحد الأقصى: {self.max_duration}s", None
            
            # 6. محاولة قراءة أول إطار للتأكد
            ret, frame = cap.read()
            cap.release()
            
            if not ret or frame is None:
                return False, "فشل قراءة إطارات الفيديو. الملف قد يكون تالفاً", None
            
            # كل شيء صحيح!
            video_info = {
                'filename': file_path.name,
                'size_mb': file_size / (1024 * 1024),
                'duration_sec': duration,
                'fps': fps,
                'frame_count': frame_count,
                'width': width,
                'height': height,
                'resolution': f"{width}x{height}",
                'format': extension[1:]  # بدون النقطة
            }
            
            logger.info(f"✓ ملف صحيح: {file_path.name} ({duration:.1f}s, {width}x{height})")
            return True, None, video_info
            
        except Exception as e:
            logger.exception(f"خطأ أثناء التحقق من الفيديو: {e}")
            return False, f"خطأ أثناء التحقق من الفيديو: {str(e)}", None
    
    def get_validation_summary(self) -> str:
        """الحصول على ملخص قواعد التحقق"""
        return f"""قواعد التحقق من الملفات:
• الأنواع المدعومة: {', '.join(self.allowed_extensions)}
• الحد الأقصى للحجم: {self.max_size_bytes / (1024*1024):.0f}MB
• الحد الأقصى للمدة: {self.max_duration}s ({self.max_duration/60:.0f} دقيقة)
• الحد الأدنى للمدة: {MIN_VIDEO_DURATION_SECONDS}s
"""


def validate_video_quick(file_path: str | Path) -> Tuple[bool, Optional[str]]:
    """
    التحقق السريع من الفيديو (بدون معلومات تفصيلية)
    
    Args:
        file_path: مسار الملف
    
    Returns:
        (is_valid, error_message)
    """
    validator = FileValidator()
    is_valid, error, _ = validator.validate_video_file(file_path)
    return is_valid, error


# مثال الاستخدام
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    validator = FileValidator(max_size_mb=100, max_duration_sec=300)
    print(validator.get_validation_summary())
    
    # اختبار
    test_file = "test.mp4"
    is_valid, error, info = validator.validate_video_file(test_file)
    
    if is_valid:
        print(f"✓ الملف صحيح!")
        print(f"  المدة: {info['duration_sec']:.1f}s")
        print(f"  الحجم: {info['size_mb']:.1f}MB")
        print(f"  الدقة: {info['resolution']}")
    else:
        print(f"✗ خطأ: {error}")
