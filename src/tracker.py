"""
Person Tracker - BoT-SORT integration for accurate person tracking
Phase 2 Implementation
"""

from ultralytics import YOLO
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class PersonTracker:
    """تتبع الأشخاص باستخدام BoT-SORT المدمج في YOLO"""
    
    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        conf_threshold: float = 0.5,
        tracker_type: str = "botsort"  # أو "bytetrack"
    ):
        """
        تهيئة المتتبع
        
        Args:
            model_path: مسار نموذج YOLO
            conf_threshold: عتبة الثقة
            tracker_type: نوع المتتبع (botsort أو bytetrack)
        """
        self.conf_threshold = conf_threshold
        self.tracker_type = tracker_type
        
        try:
            self.model = YOLO(model_path)
            logger.info(f"✓ تم تحميل YOLO: {model_path}")
            logger.info(f"✓ المتتبع: {tracker_type}")
        except Exception as e:
            logger.error(f"✗ فشل تحميل النموذج: {e}")
            raise
        
        # تخزين بيانات الأشخاص
        self.persons: Dict[int, dict] = {}
        self.frame_count = 0
    
    def track(self, frame: np.ndarray) -> Dict[int, dict]:
        """
        تتبع الأشخاص في الإطار
        
        Args:
            frame: صورة numpy array (BGR)
            
        Returns:
            قاموس بالأشخاص: {track_id: {'box': (x1,y1,x2,y2), 'conf': float}}
        """
        if frame is None or frame.size == 0:
            return {}
        
        self.frame_count += 1
        current_tracks = {}
        
        try:
            # تشغيل YOLO مع التتبع
            results = self.model.track(
                frame,
                persist=True,             # الحفاظ على المسارات بين الإطارات
                tracker=f"{self.tracker_type}.yaml",
                classes=[0],              # person فقط
                conf=self.conf_threshold,
                verbose=False
            )
            
            if results and len(results) > 0 and results[0].boxes is not None:
                boxes = results[0].boxes
                
                if boxes.id is not None:
                    for i, (box, track_id) in enumerate(zip(boxes.xyxy, boxes.id)):
                        tid = int(track_id.item())
                        x1, y1, x2, y2 = map(int, box.tolist())
                        conf = float(boxes.conf[i].item()) if boxes.conf is not None else 0.8
                        
                        current_tracks[tid] = {
                            'box': (x1, y1, x2, y2),
                            'conf': conf,
                            'center': ((x1 + x2) // 2, (y1 + y2) // 2)
                        }
                        
                        # تحديث بيانات الشخص
                        if tid not in self.persons:
                            self.persons[tid] = {
                                'first_seen': self.frame_count,
                                'detection_count': 0,
                                'last_box': None
                            }
                        
                        self.persons[tid]['last_seen'] = self.frame_count
                        self.persons[tid]['detection_count'] += 1
                        self.persons[tid]['last_box'] = (x1, y1, x2, y2)
            
            return current_tracks
            
        except Exception as e:
            logger.error(f"خطأ في التتبع: {e}")
            return {}
    
    def get_unique_persons_count(self) -> int:
        """الحصول على عدد الأشخاص الفريدين المكتشفين"""
        return len(self.persons)
    
    def get_active_tracks(self, max_age: int = 30) -> Dict[int, dict]:
        """الحصول على المسارات النشطة (شوهدت مؤخراً)"""
        active = {}
        for tid, data in self.persons.items():
            if self.frame_count - data.get('last_seen', 0) <= max_age:
                active[tid] = data
        return active
    
    def reset(self):
        """إعادة تعيين المتتبع"""
        self.persons = {}
        self.frame_count = 0
        # إعادة تحميل النموذج لمسح حالة التتبع
        self.model = YOLO(self.model.model_name if hasattr(self.model, 'model_name') else "yolov8n.pt")
