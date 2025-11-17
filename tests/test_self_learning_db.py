"""
اختبارات قاعدة بيانات نظام التعلم الذاتي
Tests for Self-Learning Database
"""
import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.self_learning.database import SelfLearningDB
from src.self_learning.models import (
    ConfirmationQueue,
    HumanCorrection,
    ModelPerformance,
    QualityMetrics,
    TrainingImage,
)


@pytest.fixture
def temp_db():
    """قاعدة بيانات مؤقتة للاختبار"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    db = SelfLearningDB(db_path)
    yield db
    
    db.close()
    if os.path.exists(db_path):
        os.unlink(db_path)


def test_database_creation(temp_db):
    """اختبار إنشاء قاعدة البيانات"""
    assert temp_db.db_path.exists()
    
    # التحقق من الجداول
    cursor = temp_db.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )
    tables = {row[0] for row in cursor.fetchall()}
    
    assert 'training_images' in tables
    assert 'human_corrections' in tables
    assert 'confirmation_queue' in tables
    assert 'model_performance' in tables


def test_insert_training_image(temp_db):
    """اختبار إضافة صورة تدريبية"""
    quality = QualityMetrics(
        sharpness=120.5,
        brightness=150.0,
        face_size=120,
        face_angle=15.5,
        overall_score=0.85
    )
    
    image = TrainingImage(
        employee_id='EMP001',
        image_path='/path/to/image.jpg',
        confidence=0.92,
        quality_score=0.85,
        quality_details=quality,
        metadata={'camera': 'cam1'}
    )
    
    image_id = temp_db.insert_training_image(image)
    assert image_id > 0
    
    # استرجاع الصورة
    retrieved = temp_db.get_training_image(image_id)
    assert retrieved is not None
    assert retrieved.employee_id == 'EMP001'
    assert retrieved.confidence == 0.92
    assert retrieved.quality_details.sharpness == 120.5


def test_get_employee_images(temp_db):
    """اختبار الحصول على صور موظف"""
    # إضافة عدة صور
    for i in range(5):
        image = TrainingImage(
            employee_id='EMP001',
            image_path=f'/path/to/image{i}.jpg',
            confidence=0.9 + i * 0.01,
            quality_score=0.8
        )
        temp_db.insert_training_image(image)
    
    # الحصول على كل الصور
    images = temp_db.get_employee_images('EMP001')
    assert len(images) == 5
    
    # الحصول على 3 فقط
    images = temp_db.get_employee_images('EMP001', limit=3)
    assert len(images) == 3


def test_count_employee_images_today(temp_db):
    """اختبار عد صور الموظف اليوم"""
    # إضافة صور
    for i in range(3):
        image = TrainingImage(
            employee_id='EMP001',
            image_path=f'/path/to/image{i}.jpg',
            confidence=0.9,
            quality_score=0.8
        )
        temp_db.insert_training_image(image)
    
    count = temp_db.count_employee_images_today('EMP001')
    assert count == 3


def test_insert_correction(temp_db):
    """اختبار إضافة تصحيح بشري"""
    # إضافة صورة أولاً
    image = TrainingImage(
        employee_id='EMP001',
        image_path='/path/to/image.jpg',
        confidence=0.68,
        quality_score=0.8
    )
    image_id = temp_db.insert_training_image(image)
    
    # إضافة تصحيح
    correction = HumanCorrection(
        image_id=image_id,
        original_prediction='EMP002',
        corrected_to='EMP001',
        confidence=0.68,
        corrected_by='admin',
        correction_reason='خطأ في التعرف'
    )
    
    correction_id = temp_db.insert_correction(correction)
    assert correction_id > 0
    
    # التحقق من تعليم الصورة كمؤكدة
    image = temp_db.get_training_image(image_id)
    assert image.validated is True


def test_confirmation_queue(temp_db):
    """اختبار قائمة التأكيد"""
    # إضافة صورة
    image = TrainingImage(
        employee_id='EMP001',
        image_path='/path/to/image.jpg',
        confidence=0.70,
        quality_score=0.8
    )
    image_id = temp_db.insert_training_image(image)
    
    # إضافة لقائمة التأكيد
    predictions = [
        {'employee_id': 'EMP001', 'confidence': 0.70},
        {'employee_id': 'EMP002', 'confidence': 0.65},
    ]
    
    queue_id = temp_db.add_to_confirmation_queue(
        image_id=image_id,
        top_predictions=predictions,
        priority=2
    )
    assert queue_id > 0
    
    # الحصول على المعلقة
    pending = temp_db.get_pending_confirmations()
    assert len(pending) == 1
    assert pending[0].priority == 2
    
    # عد المعلقة
    count = temp_db.get_pending_count()
    assert count == 1
    
    # تحديث الحالة
    temp_db.update_confirmation_status(queue_id, 'confirmed', 'admin')
    
    # التحقق
    pending = temp_db.get_pending_confirmations()
    assert len(pending) == 0


def test_model_performance(temp_db):
    """اختبار مؤشرات الأداء"""
    perf = ModelPerformance(
        model_version='v1.0.0',
        accuracy=0.92,
        precision=0.91,
        recall=0.90,
        f1_score=0.905,
        test_samples=1000,
        notes='تدريب أولي'
    )
    
    perf_id = temp_db.insert_performance(perf)
    assert perf_id > 0
    
    # الحصول على آخر أداء
    latest = temp_db.get_latest_performance()
    assert latest is not None
    assert latest.accuracy == 0.92
    assert latest.model_version == 'v1.0.0'


def test_get_stats(temp_db):
    """اختبار الإحصائيات"""
    # إضافة بيانات تجريبية
    for i in range(10):
        image = TrainingImage(
            employee_id=f'EMP00{i%3 + 1}',
            image_path=f'/path/to/image{i}.jpg',
            confidence=0.85 + i * 0.01,
            quality_score=0.75 + i * 0.02,
            validated=(i % 2 == 0)
        )
        temp_db.insert_training_image(image)
    
    stats = temp_db.get_stats()
    
    assert stats['images']['total'] == 10
    assert stats['images']['validated'] == 5
    assert stats['images']['avg_quality'] > 0.75
    assert stats['images']['avg_confidence'] > 0.85


def test_mark_as_used_in_training(temp_db):
    """اختبار تعليم الصور كمستخدمة"""
    # إضافة صور
    image_ids = []
    for i in range(5):
        image = TrainingImage(
            employee_id='EMP001',
            image_path=f'/path/to/image{i}.jpg',
            confidence=0.9,
            quality_score=0.8
        )
        image_ids.append(temp_db.insert_training_image(image))
    
    # تعليم كمستخدمة
    temp_db.mark_as_used_in_training(image_ids[:3])
    
    # التحقق
    for i, img_id in enumerate(image_ids):
        image = temp_db.get_training_image(img_id)
        if i < 3:
            assert image.used_in_training is True
        else:
            assert image.used_in_training is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
