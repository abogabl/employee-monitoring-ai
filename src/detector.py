"""
Person Detector - Simple YOLO-based person detection
Fresh start implementation - Phase 1
"""

from ultralytics import YOLO
import numpy as np
from typing import List, Tuple, Dict
import logging

logger = logging.getLogger(__name__)


class PersonDetector:
    """كاشف الأشخاص باستخدام YOLO"""
    
    def __init__(self, model_path: str = "yolov8n.pt", conf_threshold: float = 0.5):
        """
        تهيئة الكاشف
        
        Args:
            model_path: مسار نموذج YOLO
            conf_threshold: عتبة الثقة (0.0 - 1.0)
        """
        self.conf_threshold = conf_threshold
        
        try:
            self.model = YOLO(model_path)
            logger.info(f"✓ تم تحميل نموذج YOLO: {model_path}")
        except Exception as e:
            logger.error(f"✗ فشل تحميل النموذج: {e}")
            raise
    
    def detect(self, frame: np.ndarray) -> List[Dict]:
        """
        كشف الأشخاص في الصورة
        
        Args:
            frame: صورة numpy array (BGR)
            
        Returns:
            قائمة بالأشخاص المكتشفين, كل عنصر يحتوي على:
            - box: (x1, y1, x2, y2)
            - confidence: نسبة الثقة
        """
        if frame is None or frame.size == 0:
            return []
        
        try:
            # تشغيل YOLO
            results = self.model.predict(
                frame,
                classes=[0],  # 0 = person في COCO
                conf=self.conf_threshold,
                verbose=False
            )
            
            detections = []
            
            if results and len(results) > 0:
                boxes = results[0].boxes
                
                if boxes is not None:
                    for i in range(len(boxes)):
                        # الإحداثيات
                        xyxy = boxes.xyxy[i].cpu().numpy()
                        x1, y1, x2, y2 = map(int, xyxy)
                        
                        # الثقة
                        conf = float(boxes.conf[i].cpu().numpy())
                        
                        detections.append({
                            'box': (x1, y1, x2, y2),
                            'confidence': conf
                        })
            
            return detections
            
        except Exception as e:
            logger.error(f"خطأ في الكشف: {e}")
            return []
    
    def detect_count(self, frame: np.ndarray) -> Tuple[int, List[Dict]]:
        """
        كشف وعد الأشخاص
        
        Returns:
            (عدد الأشخاص, قائمة التفاصيل)
        """
        detections = self.detect(frame)
        return len(detections), detections
