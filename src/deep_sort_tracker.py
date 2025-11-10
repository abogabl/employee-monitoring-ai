"""
Deep SORT Tracker - تتبع متقدم للأشخاص
استخدام Deep SORT بدلاً من Centroid Tracking لتحسين دقة التتبع
"""
from typing import List, Dict, Any, Tuple
import numpy as np
import logging

try:
    from deep_sort_realtime.deepsort_tracker import DeepSort
    DEEPSORT_AVAILABLE = True
except ImportError:
    DEEPSORT_AVAILABLE = False
    logging.warning("⚠️ deep-sort-realtime غير متوفر. استخدم: pip install deep-sort-realtime")

logger = logging.getLogger(__name__)


class DeepSortTracker:
    """
    متعقّب أشخاص متقدم باستخدام Deep SORT
    
    المزايا:
    - يستخدم الميزات البصرية (appearance features) من CNN
    - Kalman Filter للتنبؤ بالحركة
    - Hungarian Algorithm لربط الـ tracks
    - دقة عالية في التتبع (95%+)
    - يمنع فقدان الـ ID عند الحركة السريعة
    
    الاستخدام:
    ```python
    tracker = DeepSortTracker()
    tracked_persons = tracker.update(detections, frame)
    ```
    """
    
    def __init__(
        self,
        max_age: int = 90,              # عدد الإطارات قبل حذف المسار
        n_init: int = 3,                # عدد الكشوفات لتأكيد المسار
        max_iou_distance: float = 0.7,  # حد IOU للربط
        max_cosine_distance: float = 0.3, # حد المسافة للـ features
        embedder: str = "mobilenet",    # نموذج استخراج الـ features
        embedder_gpu: bool = False      # استخدام CPU
    ):
        """
        تهيئة DeepSORT Tracker
        
        المعاملات:
            max_age: عدد الإطارات التي يبقى فيها المسار بدون كشف (الافتراضي: 90)
            n_init: عدد الكشوفات المتتالية لتأكيد مسار جديد (الافتراضي: 3)
            max_iou_distance: الحد الأقصى لمسافة IOU 0-1 (الافتراضي: 0.7)
            max_cosine_distance: الحد الأقصى للمسافة بين الـ features (الافتراضي: 0.3)
            embedder: نموذج استخراج الميزات - mobilenet, torchreid, clip (الافتراضي: mobilenet)
            embedder_gpu: استخدام GPU للـ embedder (الافتراضي: False)
        """
        if not DEEPSORT_AVAILABLE:
            raise ImportError(
                "deep-sort-realtime غير مثبت. قم بتثبيته باستخدام:\n"
                "pip install deep-sort-realtime"
            )
        
        try:
            self.tracker = DeepSort(
                max_age=max_age,
                n_init=n_init,
                max_iou_distance=max_iou_distance,
                max_cosine_distance=max_cosine_distance,
                embedder=embedder,
                embedder_gpu=embedder_gpu
            )
            logger.info(f"✅ تم تهيئة DeepSORT Tracker بنجاح")
            logger.info(f"   📊 الإعدادات:")
            logger.info(f"      - max_age: {max_age} إطار")
            logger.info(f"      - n_init: {n_init} كشوفات")
            logger.info(f"      - max_iou_distance: {max_iou_distance}")
            logger.info(f"      - max_cosine_distance: {max_cosine_distance}")
            logger.info(f"      - embedder: {embedder}")
            logger.info(f"      - GPU: {'نعم' if embedder_gpu else 'لا (CPU)'}")
        except Exception as e:
            logger.error(f"❌ فشل تهيئة DeepSORT: {e}")
            raise
    
    def update(
        self, 
        detections: List[Dict[str, Any]], 
        frame: np.ndarray = None
    ) -> Dict[int, Dict[str, Any]]:
        """
        تحديث المتعقب بالكشوفات الجديدة
        
        المدخلات:
            detections: قائمة الكشوفات
                [{'box': (x1,y1,x2,y2), 'confidence': 0.8}, ...]
            frame: الإطار الحالي (مطلوب لاستخراج الـ features)
                    np.ndarray بصيغة BGR
        
        المخرجات:
            dict: {track_id: {'box': (x1,y1,x2,y2), 'confidence': 0.8}, ...}
        
        مثال:
        ```python
        detections = [
            {'box': (100, 50, 300, 400), 'confidence': 0.85},
            {'box': (400, 60, 600, 420), 'confidence': 0.92}
        ]
        tracked = tracker.update(detections, frame)
        # tracked = {1: {'box': (100,50,300,400), 'confidence': 0.85}, ...}
        ```
        """
        if not detections:
            # لا يوجد كشوفات، تحديث بقائمة فارغة
            self.tracker.update_tracks([], frame=frame)
            return {}
        
        # تحويل الكشوفات لصيغة DeepSORT
        # DeepSORT يتوقع: ([x1, y1, width, height], confidence, class)
        raw_detections = []
        for det in detections:
            # الحصول على الـ box بطرق مختلفة للتوافقية
            box = det.get('box', None) or det.get('bbox', None)
            if box is None or len(box) != 4:
                logger.warning(f"⚠️ كشف بدون صندوق صحيح: {det}")
                continue
            
            x1, y1, x2, y2 = box
            width = x2 - x1
            height = y2 - y1
            
            # تأكد من أن الصندوق صالح
            if width <= 0 or height <= 0:
                logger.warning(f"⚠️ صندوق بأبعاد غير صالحة: {box}")
                continue
            
            confidence = det.get('confidence', det.get('conf', 0.8))
            
            # DeepSORT format: ([left, top, width, height], confidence, detection_class)
            raw_detections.append(([x1, y1, width, height], confidence, 'person'))
        
        if not raw_detections:
            # لا يوجد كشوفات صالحة
            self.tracker.update_tracks([], frame=frame)
            return {}
        
        try:
            # تحديث DeepSORT (مهم: تمرير frame لاستخراج الـ features!)
            tracks = self.tracker.update_tracks(raw_detections, frame=frame)
            
            # تحويل المخرجات لصيغتنا
            tracked_persons = {}
            for track in tracks:
                # فقط المسارات المؤكدة (confirmed)
                if not track.is_confirmed():
                    continue
                
                track_id = track.track_id
                ltrb = track.to_ltrb()  # left, top, right, bottom
                
                # التأكد من أن الإحداثيات صالحة
                if len(ltrb) == 4:
                    tracked_persons[track_id] = {
                        'box': (int(ltrb[0]), int(ltrb[1]), int(ltrb[2]), int(ltrb[3])),
                        'confidence': track.get_det_conf() if hasattr(track, 'get_det_conf') else 0.8
                    }
            
            return tracked_persons
        
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث DeepSORT: {e}")
            # إرجاع قائمة فارغة في حالة الخطأ
            return {}
    
    def get_active_tracks_count(self) -> int:
        """
        الحصول على عدد المسارات النشطة (المؤكدة)
        
        المخرجات:
            int: عدد المسارات النشطة
        """
        try:
            return len([t for t in self.tracker.tracks if t.is_confirmed()])
        except:
            return 0
    
    def reset(self):
        """
        إعادة تعيين المتعقب (حذف كل المسارات)
        
        استخدم هذه الدالة عند:
        - بداية فيديو جديد
        - تغيير كبير في المشهد
        - إعادة تشغيل المعالجة
        """
        try:
            self.tracker.delete_all_tracks()
            logger.info("🔄 تم إعادة تعيين DeepSORT Tracker")
        except Exception as e:
            logger.error(f"❌ خطأ في إعادة تعيين DeepSORT: {e}")
    
    def __str__(self) -> str:
        """تمثيل نصي للمتعقب"""
        active = self.get_active_tracks_count()
        total = len(self.tracker.tracks) if hasattr(self.tracker, 'tracks') else 0
        return f"DeepSortTracker(active={active}, total={total})"
    
    def __repr__(self) -> str:
        """تمثيل نصي للمتعقب"""
        return self.__str__()
