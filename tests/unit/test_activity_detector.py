"""
اختبارات شاملة لكاشف النشاط المتقدم
Comprehensive tests for AdvancedActivityDetector
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch


class TestAdvancedActivityDetectorInit:
    """اختبارات التهيئة"""
    
    def test_initialization_default(self):
        """اختبار التهيئة الافتراضية"""
        from src.advanced_activity_detector import AdvancedActivityDetector
        
        detector = AdvancedActivityDetector()
        
        assert detector.max_distance == 250
        assert detector.motion_window == 10
        assert detector.temporal_window == 30
        assert detector.max_tracks == 100
    
    def test_initialization_custom(self):
        """اختبار التهيئة المخصصة"""
        from src.advanced_activity_detector import AdvancedActivityDetector
        
        detector = AdvancedActivityDetector(
            max_distance=300,
            motion_window=15,
            temporal_window=50
        )
        
        assert detector.max_distance == 300
        assert detector.motion_window == 15
        assert detector.temporal_window == 50


class TestActivityDetection:
    """اختبارات كشف النشاط"""
    
    @pytest.fixture
    def detector(self):
        """إنشاء كاشف للاختبار"""
        from src.advanced_activity_detector import AdvancedActivityDetector
        return AdvancedActivityDetector(use_pose=False, use_optical_flow=False)
    
    @pytest.fixture
    def sample_frame(self):
        """إطار عينة"""
        return np.zeros((480, 640, 3), dtype=np.uint8)
    
    def test_detect_activity_basic(self, detector, sample_frame):
        """اختبار كشف النشاط الأساسي"""
        person_box = (100, 100, 200, 300)
        
        activity, confidence, details = detector.detect_activity(
            frame=sample_frame,
            person_box=person_box,
            track_id=1,
            yolo_detections=[],
            frame_time=0.0
        )
        
        assert activity in ['working', 'idle', 'standing', 'sitting', 'walking', 'sleeping', 'on_phone', 'unknown']
        assert 0 <= confidence <= 1
        assert 'motion_level' in details
    
    def test_detect_activity_with_objects(self, detector, sample_frame):
        """اختبار كشف النشاط مع أشياء"""
        person_box = (100, 100, 200, 300)
        
        # إضافة لابتوب قريب
        yolo_detections = [{
            'class': 63,  # laptop
            'box': (120, 200, 180, 250),
            'conf': 0.9
        }]
        
        activity, confidence, details = detector.detect_activity(
            frame=sample_frame,
            person_box=person_box,
            track_id=1,
            yolo_detections=yolo_detections,
            frame_time=0.0
        )
        
        # مع لابتوب، يجب أن يكون working
        assert activity == 'working'
    
    def test_detect_activity_with_phone(self, detector, sample_frame):
        """اختبار كشف النشاط مع هاتف"""
        person_box = (100, 100, 200, 300)
        
        # إضافة هاتف قريب
        yolo_detections = [{
            'class': 67,  # cell phone
            'box': (130, 150, 160, 180),
            'conf': 0.9
        }]
        
        activity, confidence, details = detector.detect_activity(
            frame=sample_frame,
            person_box=person_box,
            track_id=1,
            yolo_detections=yolo_detections,
            frame_time=0.0
        )
        
        # مع هاتف، يجب أن يكون on_phone
        assert activity == 'on_phone'


class TestMotionDetection:
    """اختبارات كشف الحركة"""
    
    @pytest.fixture
    def detector(self):
        from src.advanced_activity_detector import AdvancedActivityDetector
        return AdvancedActivityDetector(use_pose=False, use_optical_flow=False)
    
    def test_simple_motion_no_history(self, detector):
        """اختبار حركة بدون تاريخ"""
        person_box = (100, 100, 200, 200)
        motion = detector._calculate_simple_motion(person_box, track_id=1, frame_time=0.0)
        
        # أول إطار = لا حركة
        assert motion == 0.0
    
    def test_simple_motion_with_history(self, detector):
        """اختبار حركة مع تاريخ"""
        # إطار 1
        box1 = (100, 100, 200, 200)
        detector._calculate_simple_motion(box1, track_id=1, frame_time=0.0)
        
        # إطار 2 - تحرك
        box2 = (150, 150, 250, 250)
        motion = detector._calculate_simple_motion(box2, track_id=1, frame_time=0.04)
        
        assert motion > 0


class TestMemoryManagement:
    """اختبارات إدارة الذاكرة"""
    
    def test_max_tracks_limit(self):
        """اختبار حد الـ tracks"""
        from src.advanced_activity_detector import AdvancedActivityDetector
        
        detector = AdvancedActivityDetector(use_pose=False, use_optical_flow=False)
        detector.max_tracks = 5  # حد صغير للاختبار
        detector._cleanup_interval = 1  # تنظيف كل إطار
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # إضافة 10 tracks
        for i in range(10):
            detector.detect_activity(
                frame=frame,
                person_box=(i*50, 100, i*50+40, 200),
                track_id=i+1,
                yolo_detections=[],
                frame_time=i*0.04
            )
        
        # فرض التنظيف
        detector._auto_cleanup()
        
        # يجب أن يكون 5 فقط
        assert len(detector.activity_history) <= detector.max_tracks
    
    def test_memory_stats(self):
        """اختبار إحصائيات الذاكرة"""
        from src.advanced_activity_detector import AdvancedActivityDetector
        
        detector = AdvancedActivityDetector(use_pose=False, use_optical_flow=False)
        
        stats = detector.get_memory_stats()
        
        assert 'activity_history_count' in stats
        assert 'prev_boxes_count' in stats
        assert 'max_tracks' in stats
    
    def test_reset_track(self):
        """اختبار إعادة تعيين track"""
        from src.advanced_activity_detector import AdvancedActivityDetector
        
        detector = AdvancedActivityDetector(use_pose=False, use_optical_flow=False)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # إضافة track
        detector.detect_activity(
            frame=frame,
            person_box=(100, 100, 200, 200),
            track_id=1,
            yolo_detections=[],
            frame_time=0.0
        )
        
        assert 1 in detector.activity_history
        
        # إعادة التعيين
        detector.reset_track(1)
        
        assert 1 not in detector.activity_history


class TestTemporalSmoothing:
    """اختبارات التنعيم الزمني"""
    
    def test_temporal_smoothing_consistency(self):
        """اختبار ثبات التنعيم الزمني"""
        from src.advanced_activity_detector import AdvancedActivityDetector
        
        detector = AdvancedActivityDetector(
            use_pose=False, 
            use_optical_flow=False,
            temporal_window=10
        )
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # 10 إطارات working
        for i in range(10):
            detector.detect_activity(
                frame=frame,
                person_box=(100, 100, 200, 200),
                track_id=1,
                yolo_detections=[{
                    'class': 63,  # laptop
                    'box': (120, 200, 180, 250),
                    'conf': 0.9
                }],
                frame_time=i*0.04
            )
        
        # النشاط يجب أن يكون working بثبات
        activity, confidence, _ = detector.detect_activity(
            frame=frame,
            person_box=(100, 100, 200, 200),
            track_id=1,
            yolo_detections=[{
                'class': 63,
                'box': (120, 200, 180, 250),
                'conf': 0.9
            }],
            frame_time=0.44
        )
        
        assert activity == 'working'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
