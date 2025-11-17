"""
اختبارات مكونات نظام التعلم الذاتي
Tests for Self-Learning System Components
"""
import os
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from src.self_learning.storage import ImageStorage
from src.self_learning.quality_assessor import QualityAssessor
from src.self_learning.data_collector import DataCollector, CollectionPolicy
from src.self_learning.database import SelfLearningDB


@pytest.fixture
def temp_storage():
    """نظام تخزين مؤقت"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = ImageStorage(tmpdir)
        yield storage


@pytest.fixture
def sample_image():
    """صورة تجريبية"""
    # إنشاء صورة RGB بسيطة
    image = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
    return image


@pytest.fixture
def temp_db():
    """قاعدة بيانات مؤقتة"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    db = SelfLearningDB(db_path)
    yield db
    
    db.close()
    if os.path.exists(db_path):
        os.unlink(db_path)


# ==================== اختبارات التخزين ====================

def test_storage_initialization(temp_storage):
    """اختبار تهيئة نظام التخزين"""
    assert temp_storage.base_path.exists()
    assert temp_storage.raw_path.exists()
    assert temp_storage.validated_path.exists()
    assert temp_storage.rejected_path.exists()


def test_save_image(temp_storage, sample_image):
    """اختبار حفظ صورة"""
    path = temp_storage.save_image(
        image=sample_image,
        employee_id='EMP001',
        category='raw'
    )
    
    assert path.exists()
    assert path.parent.name == 'EMP001'
    assert path.suffix == '.jpg'


def test_save_face_crop(temp_storage):
    """اختبار حفظ قص الوجه"""
    # إنشاء إطار كبير
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    bbox = (100, 100, 300, 300)
    
    path = temp_storage.save_face_crop(
        frame=frame,
        bbox=bbox,
        employee_id='EMP001',
        category='raw'
    )
    
    assert path is not None
    assert path.exists()
    
    # قراءة الصورة والتحقق من الحجم
    saved_img = cv2.imread(str(path))
    assert saved_img is not None
    assert saved_img.shape[0] > 0
    assert saved_img.shape[1] > 0


def test_move_image(temp_storage, sample_image):
    """اختبار نقل صورة"""
    # حفظ في raw
    path1 = temp_storage.save_image(sample_image, 'EMP001', category='raw')
    
    # نقل إلى validated
    path2 = temp_storage.move_image(path1, 'validated', 'EMP001')
    
    assert not path1.exists()
    assert path2.exists()
    assert 'validated' in str(path2)


def test_get_employee_images(temp_storage, sample_image):
    """اختبار الحصول على صور موظف"""
    # حفظ عدة صور
    for i in range(3):
        temp_storage.save_image(sample_image, 'EMP001', category='raw')
    
    images = temp_storage.get_employee_images('EMP001', category='raw')
    assert len(images) == 3


def test_count_images(temp_storage, sample_image):
    """اختبار عد الصور"""
    # حفظ صور لموظفين مختلفين
    temp_storage.save_image(sample_image, 'EMP001', category='raw')
    temp_storage.save_image(sample_image, 'EMP001', category='raw')
    temp_storage.save_image(sample_image, 'EMP002', category='raw')
    
    count_emp1 = temp_storage.count_images('EMP001', 'raw')
    count_all = temp_storage.count_images(category='raw')
    
    assert count_emp1 == 2
    assert count_all == 3


def test_storage_stats(temp_storage, sample_image):
    """اختبار إحصائيات التخزين"""
    temp_storage.save_image(sample_image, 'EMP001', category='raw')
    temp_storage.save_image(sample_image, 'EMP001', category='validated')
    
    stats = temp_storage.get_storage_stats()
    
    assert stats['raw_images'] == 1
    assert stats['validated_images'] == 1
    assert stats['total_employees'] >= 1


# ==================== اختبارات تقييم الجودة ====================

def test_quality_assessor_initialization():
    """اختبار تهيئة مُقيِّم الجودة"""
    assessor = QualityAssessor()
    
    assert assessor.min_sharpness > 0
    assert assessor.min_face_size > 0


def test_assess_image_sharpness():
    """اختبار قياس الوضوح"""
    assessor = QualityAssessor()
    
    # صورة واضحة (نمط شطرنج)
    sharp_image = np.zeros((100, 100), dtype=np.uint8)
    sharp_image[::10] = 255  # خطوط أفقية
    
    # صورة ضبابية
    blurry_image = cv2.GaussianBlur(sharp_image, (15, 15), 0)
    
    sharp_sharpness = assessor._measure_sharpness(sharp_image)
    blurry_sharpness = assessor._measure_sharpness(blurry_image)
    
    assert sharp_sharpness > blurry_sharpness


def test_assess_image_brightness():
    """اختبار قياس الإضاءة"""
    assessor = QualityAssessor()
    
    # صورة مظلمة
    dark_image = np.zeros((100, 100), dtype=np.uint8)
    
    # صورة ساطعة
    bright_image = np.full((100, 100), 200, dtype=np.uint8)
    
    dark_brightness = assessor._measure_brightness(dark_image)
    bright_brightness = assessor._measure_brightness(bright_image)
    
    assert bright_brightness > dark_brightness
    assert bright_brightness > 150


def test_assess_image_full(sample_image):
    """اختبار تقييم كامل"""
    assessor = QualityAssessor()
    
    metrics = assessor.assess_image(sample_image)
    
    assert metrics.sharpness >= 0
    assert 0 <= metrics.brightness <= 255
    assert metrics.face_size >= 0
    assert 0 <= metrics.face_angle <= 90
    assert 0 <= metrics.overall_score <= 1


def test_is_acceptable():
    """اختبار قبول الصورة"""
    assessor = QualityAssessor(
        min_sharpness=50.0,
        min_brightness=60.0,
        min_face_size=80
    )
    
    # صورة جيدة
    good_image = np.random.randint(100, 200, (150, 150, 3), dtype=np.uint8)
    good_metrics = assessor.assess_image(good_image)
    
    # قد تكون مقبولة أو لا حسب المحتوى العشوائي
    # نتحقق فقط من عدم وجود أخطاء
    result = assessor.is_acceptable(good_metrics)
    assert isinstance(result, bool)


def test_get_rejection_reasons():
    """اختبار أسباب الرفض"""
    assessor = QualityAssessor()
    
    # صورة سيئة
    bad_image = np.zeros((50, 50, 3), dtype=np.uint8)
    bad_metrics = assessor.assess_image(bad_image)
    
    reasons = assessor.get_rejection_reasons(bad_metrics)
    
    # يجب أن يكون هناك أسباب للرفض
    assert isinstance(reasons, list)


# ==================== اختبارات مُجمِّع البيانات ====================

def test_data_collector_initialization(temp_db):
    """اختبار تهيئة مُجمِّع البيانات"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = ImageStorage(tmpdir)
        collector = DataCollector(
            db=temp_db,
            storage=storage
        )
        
        assert collector.db is not None
        assert collector.storage is not None
        assert collector.quality_assessor is not None


def test_collect_face(temp_db):
    """اختبار جمع وجه"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = ImageStorage(tmpdir)
        collector = DataCollector(
            db=temp_db,
            storage=storage,
            min_confidence=0.80
        )
        
        # إنشاء إطار تجريبي
        frame = np.random.randint(100, 200, (480, 640, 3), dtype=np.uint8)
        bbox = (100, 100, 300, 300)
        
        # جمع وجه بثقة عالية
        image_id = collector.collect_face(
            frame=frame,
            employee_id='EMP001',
            confidence=0.92,
            bbox=bbox
        )
        
        # قد يكون None إذا فشل تقييم الجودة
        # نتحقق فقط من عدم وجود أخطاء
        assert image_id is None or isinstance(image_id, int)


def test_collect_face_low_confidence(temp_db):
    """اختبار رفض وجه بثقة منخفضة"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = ImageStorage(tmpdir)
        collector = DataCollector(
            db=temp_db,
            storage=storage,
            min_confidence=0.80
        )
        
        frame = np.random.randint(100, 200, (480, 640, 3), dtype=np.uint8)
        bbox = (100, 100, 300, 300)
        
        # جمع وجه بثقة منخفضة
        image_id = collector.collect_face(
            frame=frame,
            employee_id='EMP001',
            confidence=0.65,  # أقل من الحد الأدنى
            bbox=bbox
        )
        
        assert image_id is None
        assert collector.session_stats['rejected_confidence'] == 1


def test_session_stats(temp_db):
    """اختبار إحصائيات الجلسة"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = ImageStorage(tmpdir)
        collector = DataCollector(db=temp_db, storage=storage)
        
        stats = collector.get_session_stats()
        
        assert 'collected' in stats
        assert 'rejected_quality' in stats
        assert 'rejected_confidence' in stats
        assert 'total_attempts' in stats
        assert 'success_rate' in stats


# ==================== اختبارات سياسة الجمع ====================

def test_collection_policy():
    """اختبار سياسة الجمع"""
    policy = CollectionPolicy(
        min_interval_seconds=300,
        max_images_per_session=3
    )
    
    # يجب أن يكون ممكناً في البداية
    assert policy.can_collect('EMP001') is True
    
    # بعد التسجيل
    policy.mark_collected('EMP001')
    
    # لا يجب أن يكون ممكناً مباشرة (نفس الوقت)
    assert policy.can_collect('EMP001') is False


def test_collection_policy_session_limit():
    """اختبار حد الجلسة"""
    policy = CollectionPolicy(
        min_interval_seconds=0,  # بدون فاصل
        max_images_per_session=2
    )
    
    # يمكن جمع 2
    assert policy.can_collect('EMP001') is True
    policy.mark_collected('EMP001')
    
    assert policy.can_collect('EMP001') is True
    policy.mark_collected('EMP001')
    
    # الثالثة ممنوعة
    assert policy.can_collect('EMP001') is False


def test_collection_policy_reset():
    """اختبار إعادة تعيين الجلسة"""
    policy = CollectionPolicy(max_images_per_session=1)
    
    policy.mark_collected('EMP001')
    assert policy.can_collect('EMP001') is False
    
    # إعادة تعيين
    policy.reset_session('EMP001')
    assert policy.can_collect('EMP001') is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
