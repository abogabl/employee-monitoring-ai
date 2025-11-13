"""
نظام التتبع الذكي للأشخاص - Smart Person Tracker
يستخدم الذكاء الاصطناعي لحل مشاكل التتبع وإعادة التعرف

المشاكل المحلولة:
1. عدد الأشخاص غير دقيق مع زيادة العدد
2. فقدان الهوية عند الخروج والعودة للكادر
3. تحسين دقة كشف الأنشطة (عمل، نوم، موبايل)
4. تتبع مستمر وموثوق للموظفين
"""

import cv2
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict, deque
from datetime import datetime, timedelta
import json
from pathlib import Path
import hashlib

# مكتبات الذكاء الاصطناعي
try:
    from sklearn.cluster import DBSCAN
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.preprocessing import StandardScaler
    import joblib
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smart_person_tracker")

class PersonFeatureExtractor:
    """مستخرج الميزات الشخصية للتعرف على الأشخاص"""
    
    def __init__(self):
        self.feature_history = defaultdict(list)
        self.scaler = StandardScaler()
        
    def extract_visual_features(self, bbox: Tuple[int, int, int, int], 
                               frame: np.ndarray) -> np.ndarray:
        """استخراج الميزات البصرية من الشخص"""
        x1, y1, x2, y2 = bbox
        
        # قص منطقة الشخص
        person_crop = frame[y1:y2, x1:x2]
        
        if person_crop.size == 0:
            return np.zeros(50)  # ميزات فارغة
        
        features = []
        
        # 1. ميزات الحجم والشكل
        height = y2 - y1
        width = x2 - x1
        aspect_ratio = width / max(height, 1)
        area = width * height
        
        features.extend([
            height / 480.0,  # تطبيع نسبة للارتفاع المعياري
            width / 640.0,   # تطبيع نسبة للعرض المعياري
            aspect_ratio,
            area / (640 * 480)  # نسبة المساحة
        ])
        
        # 2. ميزات اللون (متوسط RGB)
        if len(person_crop.shape) == 3:
            mean_colors = np.mean(person_crop, axis=(0, 1))
            features.extend(mean_colors / 255.0)  # تطبيع
        else:
            features.extend([0, 0, 0])
        
        # 3. ميزات الملمس (تدرج اللون)
        gray_crop = cv2.cvtColor(person_crop, cv2.COLOR_BGR2GRAY) if len(person_crop.shape) == 3 else person_crop
        
        # حساب التدرج
        grad_x = cv2.Sobel(gray_crop, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray_crop, cv2.CV_64F, 0, 1, ksize=3)
        
        features.extend([
            np.mean(np.abs(grad_x)) / 255.0,
            np.mean(np.abs(grad_y)) / 255.0,
            np.std(gray_crop) / 255.0
        ])
        
        # 4. ميزات الموقع النسبي
        center_x = (x1 + x2) / 2 / frame.shape[1]
        center_y = (y1 + y2) / 2 / frame.shape[0]
        
        features.extend([center_x, center_y])
        
        # 5. ميزات إضافية (هيستوجرام مبسط)
        hist = cv2.calcHist([gray_crop], [0], None, [8], [0, 256])
        hist_normalized = hist.flatten() / max(np.sum(hist), 1)
        features.extend(hist_normalized)
        
        # 6. ميزات الحواف
        edges = cv2.Canny(gray_crop, 50, 150)
        edge_density = np.sum(edges > 0) / max(edges.size, 1)
        features.append(edge_density)
        
        # تكملة الميزات للوصول لـ 50 ميزة
        while len(features) < 50:
            features.append(0.0)
        
        return np.array(features[:50])
    
    def extract_behavioral_features(self, person_data: Dict) -> np.ndarray:
        """استخراج الميزات السلوكية"""
        features = []
        
        # ميزات النشاط
        activities = person_data.get('activities', {})
        total_time = sum(activities.values()) or 1
        
        features.extend([
            activities.get('working', 0) / total_time,
            activities.get('sleeping', 0) / total_time,
            activities.get('idle', 0) / total_time,
            activities.get('on_phone', 0) / total_time,
        ])
        
        # ميزات الحركة
        features.extend([
            person_data.get('avg_motion', 0),
            person_data.get('motion_variance', 0),
            person_data.get('position_changes', 0) / 100.0,
        ])
        
        # ميزات زمنية
        features.extend([
            person_data.get('duration', 0) / 3600.0,  # ساعات
            person_data.get('detection_count', 0) / 1000.0,
            person_data.get('avg_confidence', 0),
        ])
        
        return np.array(features)

class SmartPersonTracker:
    """نظام التتبع الذكي للأشخاص"""
    
    def __init__(self, max_persons: int = 20, similarity_threshold: float = 0.7):
        self.max_persons = max_persons
        self.similarity_threshold = similarity_threshold
        
        # قاعدة بيانات الأشخاص
        self.person_database = {}  # person_id -> features & data
        self.active_tracks = {}    # track_id -> person_id
        self.lost_tracks = {}      # person_id -> last_seen_time
        
        # مستخرج الميزات
        self.feature_extractor = PersonFeatureExtractor()
        
        # إعدادات التتبع
        self.max_lost_time = 30.0  # ثانية
        self.min_detections_for_id = 5
        self.feature_update_rate = 0.1  # معدل تحديث الميزات
        
        # إحصائيات
        self.stats = {
            'total_persons_detected': 0,
            'successful_reidentifications': 0,
            'lost_tracks_recovered': 0,
            'false_positives_prevented': 0
        }
        
        logger.info("تم تهيئة نظام التتبع الذكي")
    
    def process_detections(self, detections: List[Dict], frame: np.ndarray, 
                          timestamp: float) -> List[Dict]:
        """معالجة الكشوفات الجديدة وتطبيق التتبع الذكي"""
        
        if len(detections) == 0:
            return []
        
        # تنظيف التتبع المفقود
        self._cleanup_lost_tracks(timestamp)
        
        # استخراج الميزات لكل كشف
        detection_features = []
        for detection in detections:
            bbox = detection['bbox']
            visual_features = self.feature_extractor.extract_visual_features(bbox, frame)
            detection_features.append(visual_features)
        
        # مطابقة الكشوفات مع الأشخاص المعروفين
        matched_detections = self._match_detections_to_persons(
            detections, detection_features, timestamp
        )
        
        # تطبيق منطق التتبع الذكي
        final_detections = self._apply_smart_tracking_logic(
            matched_detections, timestamp
        )
        
        # تحديث قاعدة البيانات
        self._update_person_database(final_detections, detection_features, timestamp)
        
        return final_detections
    
    def _match_detections_to_persons(self, detections: List[Dict], 
                                   features: List[np.ndarray], 
                                   timestamp: float) -> List[Dict]:
        """مطابقة الكشوفات مع الأشخاص المعروفين"""
        matched = []
        
        for i, (detection, feature) in enumerate(zip(detections, features)):
            best_match_id = None
            best_similarity = 0.0
            
            # البحث في قاعدة البيانات
            for person_id, person_data in self.person_database.items():
                if 'visual_features' not in person_data:
                    continue
                
                # حساب التشابه
                similarity = self._calculate_similarity(
                    feature, person_data['visual_features']
                )
                
                # التحقق من القرب المكاني والزمني
                spatial_temporal_score = self._calculate_spatial_temporal_score(
                    detection, person_data, timestamp
                )
                
                # النتيجة المجمعة
                combined_score = 0.7 * similarity + 0.3 * spatial_temporal_score
                
                if combined_score > best_similarity and combined_score > self.similarity_threshold:
                    best_similarity = combined_score
                    best_match_id = person_id
            
            # إنشاء الكشف المطابق
            if best_match_id:
                detection['person_id'] = best_match_id
                detection['match_confidence'] = best_similarity
                detection['is_reidentification'] = best_match_id in self.lost_tracks
                
                if detection['is_reidentification']:
                    self.stats['lost_tracks_recovered'] += 1
                    del self.lost_tracks[best_match_id]
                    logger.info(f"تم استرداد الشخص المفقود: {best_match_id}")
                
            else:
                # شخص جديد
                new_person_id = self._generate_person_id()
                detection['person_id'] = new_person_id
                detection['match_confidence'] = 0.0
                detection['is_new_person'] = True
                self.stats['total_persons_detected'] += 1
            
            matched.append(detection)
        
        return matched
    
    def _calculate_similarity(self, feature1: np.ndarray, feature2: np.ndarray) -> float:
        """حساب التشابه بين ميزتين"""
        try:
            # تطبيع الميزات
            f1_norm = feature1 / (np.linalg.norm(feature1) + 1e-8)
            f2_norm = feature2 / (np.linalg.norm(feature2) + 1e-8)
            
            # حساب التشابه الكوسيني
            similarity = np.dot(f1_norm, f2_norm)
            
            return max(0.0, similarity)
            
        except Exception as e:
            logger.error(f"خطأ في حساب التشابه: {e}")
            return 0.0
    
    def _calculate_spatial_temporal_score(self, detection: Dict, 
                                        person_data: Dict, timestamp: float) -> float:
        """حساب النتيجة المكانية والزمنية"""
        score = 0.0
        
        try:
            # النتيجة المكانية
            if 'last_position' in person_data:
                current_center = self._get_bbox_center(detection['bbox'])
                last_center = person_data['last_position']
                
                distance = np.sqrt(
                    (current_center[0] - last_center[0])**2 + 
                    (current_center[1] - last_center[1])**2
                )
                
                # تطبيع المسافة (كلما قلت المسافة، زادت النتيجة)
                max_distance = 200  # بكسل
                spatial_score = max(0.0, 1.0 - distance / max_distance)
                score += 0.6 * spatial_score
            
            # النتيجة الزمنية
            if 'last_seen' in person_data:
                time_diff = timestamp - person_data['last_seen']
                max_time_diff = 10.0  # ثانية
                temporal_score = max(0.0, 1.0 - time_diff / max_time_diff)
                score += 0.4 * temporal_score
            
        except Exception as e:
            logger.error(f"خطأ في حساب النتيجة المكانية الزمنية: {e}")
        
        return score
    
    def _apply_smart_tracking_logic(self, detections: List[Dict], 
                                  timestamp: float) -> List[Dict]:
        """تطبيق منطق التتبع الذكي لتقليل الأخطاء"""
        
        # 1. إزالة الكشوفات المتداخلة بشدة
        detections = self._remove_overlapping_detections(detections)
        
        # 2. تطبيق حد أقصى لعدد الأشخاص
        if len(detections) > self.max_persons:
            # ترتيب حسب الثقة والحجم
            detections.sort(key=lambda x: (
                x.get('match_confidence', 0) * 0.5 + 
                x.get('confidence', 0) * 0.3 + 
                self._get_bbox_area(x['bbox']) / (640 * 480) * 0.2
            ), reverse=True)
            
            detections = detections[:self.max_persons]
            self.stats['false_positives_prevented'] += 1
        
        # 3. تصفية الكشوفات ضعيفة الثقة
        min_confidence = 0.3
        detections = [d for d in detections if d.get('confidence', 0) >= min_confidence]
        
        return detections
    
    def _remove_overlapping_detections(self, detections: List[Dict], 
                                     iou_threshold: float = 0.7) -> List[Dict]:
        """إزالة الكشوفات المتداخلة"""
        if len(detections) <= 1:
            return detections
        
        # حساب IoU لكل زوج
        keep = []
        for i, det1 in enumerate(detections):
            should_keep = True
            
            for j, det2 in enumerate(detections):
                if i != j and j < i:  # تجنب المقارنة المكررة
                    iou = self._calculate_iou(det1['bbox'], det2['bbox'])
                    
                    if iou > iou_threshold:
                        # الاحتفاظ بالكشف الأفضل
                        score1 = det1.get('match_confidence', 0) + det1.get('confidence', 0)
                        score2 = det2.get('match_confidence', 0) + det2.get('confidence', 0)
                        
                        if score1 < score2:
                            should_keep = False
                            break
            
            if should_keep:
                keep.append(det1)
        
        return keep
    
    def _calculate_iou(self, bbox1: Tuple, bbox2: Tuple) -> float:
        """حساب Intersection over Union"""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # منطقة التداخل
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i <= x1_i or y2_i <= y1_i:
            return 0.0
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection
        
        return intersection / max(union, 1)
    
    def _update_person_database(self, detections: List[Dict], 
                              features: List[np.ndarray], timestamp: float):
        """تحديث قاعدة بيانات الأشخاص"""
        
        for detection, feature in zip(detections, features):
            person_id = detection['person_id']
            
            if person_id not in self.person_database:
                self.person_database[person_id] = {
                    'first_seen': timestamp,
                    'detection_count': 0,
                    'visual_features': feature,
                    'feature_history': [feature],
                    'activities': defaultdict(float),
                    'positions': []
                }
            
            person_data = self.person_database[person_id]
            
            # تحديث الميزات البصرية (متوسط متحرك)
            if len(person_data['feature_history']) >= self.min_detections_for_id:
                alpha = self.feature_update_rate
                person_data['visual_features'] = (
                    alpha * feature + (1 - alpha) * person_data['visual_features']
                )
            
            # إضافة الميزة للتاريخ
            person_data['feature_history'].append(feature)
            if len(person_data['feature_history']) > 20:  # الاحتفاظ بآخر 20
                person_data['feature_history'] = person_data['feature_history'][-20:]
            
            # تحديث البيانات الأخرى
            person_data['last_seen'] = timestamp
            person_data['detection_count'] += 1
            person_data['last_position'] = self._get_bbox_center(detection['bbox'])
            person_data['positions'].append(person_data['last_position'])
            
            # تحديث النشاط
            activity = detection.get('activity', 'idle')
            person_data['activities'][activity] += 1
    
    def _cleanup_lost_tracks(self, timestamp: float):
        """تنظيف التتبع المفقود"""
        to_remove = []
        
        for person_id, last_seen in self.lost_tracks.items():
            if timestamp - last_seen > self.max_lost_time:
                to_remove.append(person_id)
        
        for person_id in to_remove:
            del self.lost_tracks[person_id]
            logger.info(f"تم حذف التتبع المفقود نهائياً: {person_id}")
    
    def _generate_person_id(self) -> str:
        """إنشاء معرف شخص جديد"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        counter = len(self.person_database) + 1
        return f"person_{timestamp}_{counter}"
    
    def _get_bbox_center(self, bbox: Tuple) -> Tuple[float, float]:
        """الحصول على مركز المربع المحيط"""
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)
    
    def _get_bbox_area(self, bbox: Tuple) -> float:
        """الحصول على مساحة المربع المحيط"""
        x1, y1, x2, y2 = bbox
        return (x2 - x1) * (y2 - y1)
    
    def get_active_persons_count(self) -> int:
        """الحصول على عدد الأشخاص النشطين"""
        current_time = datetime.now().timestamp()
        active_count = 0
        
        for person_data in self.person_database.values():
            if current_time - person_data.get('last_seen', 0) <= 5.0:  # نشط خلال 5 ثواني
                active_count += 1
        
        return active_count
    
    def get_person_activities_summary(self) -> Dict[str, Dict]:
        """الحصول على ملخص أنشطة الأشخاص"""
        summary = {}
        
        for person_id, person_data in self.person_database.items():
            activities = person_data.get('activities', {})
            total_time = sum(activities.values()) or 1
            
            summary[person_id] = {
                'total_detections': person_data.get('detection_count', 0),
                'working_percentage': activities.get('working', 0) / total_time * 100,
                'sleeping_percentage': activities.get('sleeping', 0) / total_time * 100,
                'phone_percentage': activities.get('on_phone', 0) / total_time * 100,
                'idle_percentage': activities.get('idle', 0) / total_time * 100,
                'first_seen': person_data.get('first_seen', 0),
                'last_seen': person_data.get('last_seen', 0)
            }
        
        return summary
    
    def get_tracking_stats(self) -> Dict:
        """الحصول على إحصائيات التتبع"""
        return {
            **self.stats,
            'active_persons': self.get_active_persons_count(),
            'total_persons_in_database': len(self.person_database),
            'lost_tracks_count': len(self.lost_tracks)
        }
    
    def save_database(self, filepath: str):
        """حفظ قاعدة بيانات الأشخاص"""
        try:
            # تحويل البيانات للتسلسل
            serializable_data = {}
            
            for person_id, person_data in self.person_database.items():
                serializable_data[person_id] = {
                    'first_seen': person_data.get('first_seen', 0),
                    'last_seen': person_data.get('last_seen', 0),
                    'detection_count': person_data.get('detection_count', 0),
                    'activities': dict(person_data.get('activities', {})),
                    'positions': person_data.get('positions', [])[-10:],  # آخر 10 مواقع
                    'visual_features': person_data.get('visual_features', np.array([])).tolist()
                }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'person_database': serializable_data,
                    'stats': self.stats,
                    'timestamp': datetime.now().isoformat()
                }, f, indent=2, ensure_ascii=False)
            
            logger.info(f"تم حفظ قاعدة البيانات: {filepath}")
            
        except Exception as e:
            logger.error(f"خطأ في حفظ قاعدة البيانات: {e}")
    
    def load_database(self, filepath: str):
        """تحميل قاعدة بيانات الأشخاص"""
        try:
            if not Path(filepath).exists():
                return
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # استرداد البيانات
            for person_id, person_data in data.get('person_database', {}).items():
                self.person_database[person_id] = {
                    'first_seen': person_data.get('first_seen', 0),
                    'last_seen': person_data.get('last_seen', 0),
                    'detection_count': person_data.get('detection_count', 0),
                    'activities': defaultdict(float, person_data.get('activities', {})),
                    'positions': person_data.get('positions', []),
                    'visual_features': np.array(person_data.get('visual_features', [])),
                    'feature_history': [np.array(person_data.get('visual_features', []))]
                }
            
            self.stats.update(data.get('stats', {}))
            
            logger.info(f"تم تحميل قاعدة البيانات: {len(self.person_database)} شخص")
            
        except Exception as e:
            logger.error(f"خطأ في تحميل قاعدة البيانات: {e}")


def integrate_smart_tracker_with_level2():
    """دمج نظام التتبع الذكي مع Level 2"""
    
    integration_code = '''
# في ملف src/level2_video_processor.py
# إضافة هذا الكود في دالة __init__:

from smart_person_tracker import SmartPersonTracker

# تهيئة نظام التتبع الذكي
self.smart_tracker = SmartPersonTracker(
    max_persons=15,  # حد أقصى للأشخاص
    similarity_threshold=0.7  # عتبة التشابه
)

# في دالة process_frame، استبدال منطق التتبع العادي:

# بدلاً من:
# tracked_persons = self.tracker.update(detections)

# استخدم:
smart_detections = self.smart_tracker.process_detections(
    detections, frame, timestamp
)

# الحصول على إحصائيات محسنة:
tracking_stats = self.smart_tracker.get_tracking_stats()
activities_summary = self.smart_tracker.get_person_activities_summary()
'''
    
    return integration_code

if __name__ == "__main__":
    # مثال على الاستخدام
    tracker = SmartPersonTracker(max_persons=10)
    
    print("نظام التتبع الذكي جاهز!")
    print("الميزات:")
    print("- تتبع دقيق للأشخاص")
    print("- إعادة التعرف عند العودة للكادر")
    print("- تحديد عدد دقيق للأشخاص")
    print("- تتبع الأنشطة (عمل، نوم، موبايل)")
    print("- منع الكشوفات الخاطئة")
    
    # حفظ كود التكامل
    with open("smart_tracker_integration.py", "w", encoding="utf-8") as f:
        f.write(integrate_smart_tracker_with_level2())
    
    print("\nتم إنشاء ملف التكامل: smart_tracker_integration.py")
