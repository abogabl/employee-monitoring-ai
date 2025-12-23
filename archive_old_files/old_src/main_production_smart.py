"""
main_production_smart.py
السكريبت الرئيسي المحسن لتشغيل نظام الكاميرات مع المعالج الذكي

استخدام:
python -m src.main_production_smart \
    --source 0 \
    --camera-id cam1 \
    --device cpu \
    --imgsz 416 \
    --conf 0.35 \
    --yolo-model s \
    --enable-face-recognition \
    --enable-activity-recognition \
    --enable-attendance \
    --display
"""
from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import cv2
import numpy as np

from .smart_camera_processor import SmartCameraProcessor
from .attendance_manager import AttendanceManager
from .performance_monitor import PerformanceMonitor
from .error_handler import ErrorHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("main_production_smart")


class SmartCameraSystem:
    """نظام كاميرات ذكي محسن"""
    
    def __init__(self, args):
        self.args = args
        self.running = False
        self.cap = None
        self.processor = None
        self.attendance_manager = None
        self.perf_monitor = PerformanceMonitor()
        self.error_handler = ErrorHandler()
        
        # إعداد معالج الإشارات
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("تهيئة نظام الكاميرات الذكي...")
        
    def _signal_handler(self, signum, frame):
        """معالج إشارات الإيقاف"""
        logger.info(f"تم استلام إشارة الإيقاف {signum}")
        self.stop()
        
    def initialize(self) -> bool:
        """تهيئة النظام"""
        try:
            # تهيئة نظام الحضور
            if self.args.enable_attendance:
                self.attendance_manager = AttendanceManager()
                logger.info("✓ تم تهيئة نظام الحضور")
            
            # تهيئة المعالج الذكي
            self.processor = SmartCameraProcessor(
                camera_id=self.args.camera_id,
                device=self.args.device,
                imgsz=self.args.imgsz,
                conf_threshold=self.args.conf,
                enable_face_recognition=self.args.enable_face_recognition,
                enable_activity_recognition=self.args.enable_activity_recognition,
                enable_attendance=self.args.enable_attendance,
                yolo_model=self.args.yolo_model,
                activity_window=15,
                attendance_manager=self.attendance_manager
            )
            logger.info("✓ تم تهيئة المعالج الذكي")
            
            # تهيئة الكاميرا
            self.cap = cv2.VideoCapture(self.args.source)
            if not self.cap.isOpened():
                logger.error(f"فشل في فتح مصدر الفيديو: {self.args.source}")
                return False
            
            # إعدادات الكاميرا
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            logger.info(f"✓ تم فتح مصدر الفيديو: {self.args.source}")
            return True
            
        except Exception as e:
            logger.error(f"خطأ في التهيئة: {e}")
            return False
    
    def run(self):
        """تشغيل النظام"""
        if not self.initialize():
            return False
        
        self.running = True
        frame_count = 0
        start_time = time.time()
        
        logger.info("بدء معالجة الكاميرا...")
        
        try:
            while self.running:
                ret, frame = self.cap.read()
                if not ret:
                    logger.warning("فشل في قراءة الإطار")
                    break
                
                frame_count += 1
                
                # معالجة الإطار
                try:
                    processed_frame, frame_stats = self.processor.process_frame(frame)
                    
                    # عرض الإطار
                    if self.args.display:
                        cv2.imshow(f'Smart Camera {self.args.camera_id}', processed_frame)
                        
                        # التحكم بالمفاتيح
                        key = cv2.waitKey(1) & 0xFF
                        if key == ord('q'):
                            logger.info("تم الإيقاف بواسطة المستخدم")
                            break
                        elif key == ord('s'):
                            # حفظ إحصائيات
                            self._save_statistics()
                        elif key == ord('r'):
                            # إعادة تعيين البيانات
                            self._reset_data()
                    
                    # طباعة الإحصائيات كل 100 إطار
                    if frame_count % 100 == 0:
                        elapsed = time.time() - start_time
                        fps = frame_count / elapsed
                        logger.info(f"إطار {frame_count}: FPS={fps:.1f}, أشخاص={frame_stats['persons_detected']}")
                        
                        # طباعة إحصائيات مفصلة كل 500 إطار
                        if frame_count % 500 == 0:
                            stats = self.processor.get_statistics()
                            logger.info(f"إحصائيات: {stats['total_persons']} أشخاص، {stats['known_persons']} معروفين")
                
                except Exception as e:
                    logger.error(f"خطأ في معالجة الإطار {frame_count}: {e}")
                    continue
                
        except KeyboardInterrupt:
            logger.info("تم الإيقاف بواسطة المستخدم")
        except Exception as e:
            logger.error(f"خطأ في التشغيل: {e}")
        finally:
            self.cleanup()
        
        return True
    
    def _save_statistics(self):
        """حفظ الإحصائيات"""
        try:
            stats = self.processor.get_statistics()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            stats_file = Path(f"reports/camera_stats_{self.args.camera_id}_{timestamp}.json")
            stats_file.parent.mkdir(exist_ok=True)
            
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            
            logger.info(f"تم حفظ الإحصائيات: {stats_file}")
        except Exception as e:
            logger.error(f"خطأ في حفظ الإحصائيات: {e}")
    
    def _reset_data(self):
        """إعادة تعيين البيانات"""
        if self.processor:
            self.processor.person_data.clear()
            self.processor.prev_boxes.clear()
            logger.info("تم إعادة تعيين بيانات التتبع")
    
    def stop(self):
        """إيقاف النظام"""
        self.running = False
        logger.info("جاري إيقاف النظام...")
    
    def cleanup(self):
        """تنظيف الموارد"""
        logger.info("تنظيف الموارد...")
        
        if self.cap:
            self.cap.release()
        
        if self.processor:
            self.processor.cleanup()
        
        cv2.destroyAllWindows()
        logger.info("تم تنظيف جميع الموارد")


def parse_args():
    """تحليل معاملات سطر الأوامر"""
    parser = argparse.ArgumentParser(description="نظام كاميرات ذكي محسن")
    
    # مصدر الفيديو
    parser.add_argument("--source", type=str, default="0", 
                       help="مصدر الفيديو (0 للكاميرا الافتراضية، أو مسار ملف)")
    parser.add_argument("--camera-id", type=str, default="cam1",
                       help="معرف الكاميرا")
    
    # إعدادات YOLO
    parser.add_argument("--device", type=str, default="cpu", choices=["cpu", "cuda"],
                       help="الجهاز المستخدم")
    parser.add_argument("--imgsz", type=int, default=416,
                       help="حجم الصورة للمعالجة")
    parser.add_argument("--conf", type=float, default=0.35,
                       help="عتبة الثقة")
    parser.add_argument("--yolo-model", type=str, default="s", choices=["n", "s", "m", "l", "x"],
                       help="حجم نموذج YOLO")
    
    # الميزات
    parser.add_argument("--enable-face-recognition", action="store_true",
                       help="تفعيل التعرف على الوجوه")
    parser.add_argument("--enable-activity-recognition", action="store_true", 
                       help="تفعيل كشف الأنشطة")
    parser.add_argument("--enable-attendance", action="store_true",
                       help="تفعيل نظام الحضور")
    
    # العرض
    parser.add_argument("--display", action="store_true",
                       help="عرض الفيديو المعالج")
    parser.add_argument("--no-display", action="store_true",
                       help="عدم عرض الفيديو (للخوادم)")
    
    args = parser.parse_args()
    
    # تحويل source إلى int إذا كان رقماً
    try:
        args.source = int(args.source)
    except ValueError:
        pass  # يبقى كنص (مسار ملف)
    
    # إعداد العرض
    if args.no_display:
        args.display = False
    
    return args


def main():
    """الدالة الرئيسية"""
    args = parse_args()
    
    logger.info("=== نظام الكاميرات الذكي المحسن ===")
    logger.info(f"المصدر: {args.source}")
    logger.info(f"الكاميرا: {args.camera_id}")
    logger.info(f"النموذج: yolov8{args.yolo_model}")
    logger.info(f"الجهاز: {args.device}")
    logger.info(f"الميزات: وجوه={args.enable_face_recognition}, أنشطة={args.enable_activity_recognition}, حضور={args.enable_attendance}")
    
    # إنشاء وتشغيل النظام
    system = SmartCameraSystem(args)
    success = system.run()
    
    if success:
        logger.info("تم إنهاء النظام بنجاح")
        return 0
    else:
        logger.error("فشل في تشغيل النظام")
        return 1


if __name__ == "__main__":
    sys.exit(main())
