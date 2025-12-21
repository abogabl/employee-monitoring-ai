"""
اختبارات شاملة لنظام التتبع المحسّن (PersonTracker)
Comprehensive tests for enhanced PersonTracker
"""
import pytest
import numpy as np
from src.detection_tracking import PersonTracker


class TestPersonTrackerBasic:
    """اختبارات أساسية"""
    
    def test_initialization(self):
        """اختبار التهيئة"""
        tracker = PersonTracker()
        assert tracker.max_disappeared == 60
        assert tracker.max_distance == 100.0
        assert tracker.min_iou == 0.2
        assert tracker.use_velocity == True
        assert len(tracker.tracks) == 0
    
    def test_custom_initialization(self):
        """اختبار التهيئة المخصصة"""
        tracker = PersonTracker(
            max_disappeared=30,
            max_distance=150.0,
            min_iou=0.3,
            use_velocity=False
        )
        assert tracker.max_disappeared == 30
        assert tracker.max_distance == 150.0
        assert tracker.min_iou == 0.3
        assert tracker.use_velocity == False


class TestPersonTrackerTracking:
    """اختبارات التتبع"""
    
    def test_register_new_track(self):
        """اختبار تسجيل مسار جديد"""
        tracker = PersonTracker()
        detections = [{'box': (100, 100, 200, 200)}]
        
        result = tracker.update(detections)
        
        assert len(result) == 1
        assert 1 in result  # أول track_id = 1
        assert result[1]['box'] == (100, 100, 200, 200)
    
    def test_multiple_tracks(self):
        """اختبار عدة مسارات"""
        tracker = PersonTracker()
        detections = [
            {'box': (100, 100, 200, 200)},
            {'box': (300, 300, 400, 400)},
        ]
        
        result = tracker.update(detections)
        
        assert len(result) == 2
    
    def test_track_continuity(self):
        """اختبار استمرارية المسار"""
        tracker = PersonTracker(max_distance=150.0)
        
        # إطار 1
        tracker.update([{'box': (100, 100, 200, 200)}])
        
        # إطار 2 - نفس الشخص يتحرك قليلاً
        result = tracker.update([{'box': (110, 110, 210, 210)}])
        
        assert len(result) == 1
        assert 1 in result  # نفس الـ ID
    
    def test_track_disappearance(self):
        """اختبار اختفاء المسار"""
        tracker = PersonTracker(max_disappeared=2)
        
        # إطار 1
        tracker.update([{'box': (100, 100, 200, 200)}])
        
        # إطارات 2-4 بدون كشف
        tracker.update([])
        tracker.update([])
        result = tracker.update([])
        
        # يجب أن يختفي المسار
        assert len(result) == 0


class TestPersonTrackerIoU:
    """اختبارات IoU"""
    
    def test_iou_calculation_identical(self):
        """IoU لصناديق متطابقة = 1"""
        box1 = (100, 100, 200, 200)
        iou = PersonTracker._calculate_iou(box1, box1)
        assert iou == 1.0
    
    def test_iou_calculation_no_overlap(self):
        """IoU لصناديق غير متداخلة = 0"""
        box1 = (100, 100, 200, 200)
        box2 = (300, 300, 400, 400)
        iou = PersonTracker._calculate_iou(box1, box2)
        assert iou == 0.0
    
    def test_iou_calculation_partial_overlap(self):
        """IoU لصناديق متداخلة جزئياً"""
        box1 = (100, 100, 200, 200)
        box2 = (150, 150, 250, 250)
        iou = PersonTracker._calculate_iou(box1, box2)
        assert 0 < iou < 1
    
    def test_iou_matching(self):
        """اختبار المطابقة باستخدام IoU"""
        tracker = PersonTracker(min_iou=0.1)
        
        # إطار 1
        tracker.update([{'box': (100, 100, 200, 200)}])
        
        # إطار 2 - صندوق متداخل
        result = tracker.update([{'box': (120, 120, 220, 220)}])
        
        assert len(result) == 1
        assert 1 in result


class TestPersonTrackerVelocity:
    """اختبارات التنبؤ بالسرعة"""
    
    def test_velocity_initialization(self):
        """اختبار تهيئة السرعة"""
        tracker = PersonTracker()
        tracker.update([{'box': (100, 100, 200, 200)}])
        
        assert tracker.tracks[1]['velocity'] == (0.0, 0.0)
    
    def test_velocity_prediction(self):
        """اختبار تحديث السرعة"""
        tracker = PersonTracker()
        
        # إطار 1
        tracker.update([{'box': (100, 100, 200, 200)}])
        
        # إطار 2 - الشخص يتحرك يميناً
        tracker.update([{'box': (120, 100, 220, 200)}])
        
        # السرعة يجب أن تكون موجبة في X
        vx, vy = tracker.tracks[1]['velocity']
        assert vx > 0


class TestPersonTrackerConfidence:
    """اختبارات درجة الثقة"""
    
    def test_initial_confidence(self):
        """اختبار الثقة الابتدائية"""
        tracker = PersonTracker()
        tracker.update([{'box': (100, 100, 200, 200)}])
        
        confidence = tracker.get_track_confidence(1)
        assert confidence == 0.5
    
    def test_confidence_increase_on_match(self):
        """زيادة الثقة عند المطابقة"""
        tracker = PersonTracker()
        
        # إطار 1
        tracker.update([{'box': (100, 100, 200, 200)}])
        
        # إطار 2 - نفس الموقع
        tracker.update([{'box': (100, 100, 200, 200)}])
        
        confidence = tracker.get_track_confidence(1)
        assert confidence > 0.5
    
    def test_confidence_decrease_on_missing(self):
        """انخفاض الثقة عند الفقدان"""
        tracker = PersonTracker(max_disappeared=10)
        
        # إطار 1
        tracker.update([{'box': (100, 100, 200, 200)}])
        initial_conf = tracker.get_track_confidence(1)
        
        # إطار 2 - لا يوجد كشف
        tracker.update([])
        
        confidence = tracker.get_track_confidence(1)
        assert confidence < initial_conf


class TestPersonTrackerEdgeCases:
    """اختبارات الحالات الحدية"""
    
    def test_empty_detections(self):
        """اختبار كشف فارغ"""
        tracker = PersonTracker()
        result = tracker.update([])
        assert len(result) == 0
    
    def test_invalid_box(self):
        """اختبار صندوق غير صالح"""
        tracker = PersonTracker()
        # صندوق صغير جداً
        detections = [{'box': (100, 100, 101, 101)}]
        result = tracker.update(detections)
        assert len(result) == 1  # يجب أن يتم التسجيل
    
    def test_large_number_of_tracks(self):
        """اختبار عدد كبير من المسارات"""
        tracker = PersonTracker()
        
        # 50 شخص
        detections = [
            {'box': (i * 50, 100, i * 50 + 40, 200)}
            for i in range(50)
        ]
        
        result = tracker.update(detections)
        assert len(result) == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
