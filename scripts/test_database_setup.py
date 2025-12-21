#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار سريع لإعداد قاعدة البيانات
Quick test for database setup
"""
import sys
import io
from datetime import datetime
from pathlib import Path

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.self_learning.database import SelfLearningDB
from src.self_learning.models import TrainingImage, QualityMetrics


def main():
    print("=" * 60)
    print("🧪 اختبار قاعدة بيانات التعلم الذاتي")
    print("=" * 60)
    
    # 1. إنشاء قاعدة البيانات
    print("\n📁 إنشاء قاعدة البيانات...")
    db = SelfLearningDB()
    print(f"✓ تم الإنشاء: {db.db_path}")
    
    # 2. إضافة صورة تجريبية
    print("\n📸 إضافة صورة تجريبية...")
    quality = QualityMetrics(
        sharpness=125.0,
        brightness=160.0,
        face_size=150,
        face_angle=12.5,
        overall_score=0.88
    )
    
    image = TrainingImage(
        employee_id='TEST001',
        image_path='test/path/image.jpg',
        confidence=0.95,
        quality_score=0.88,
        quality_details=quality,
        metadata={'camera': 'test_cam', 'location': 'entrance'}
    )
    
    image_id = db.insert_training_image(image)
    print(f"✓ تم إضافة صورة: ID={image_id}")
    
    # 3. استرجاع الصورة
    print("\n🔍 استرجاع الصورة...")
    retrieved = db.get_training_image(image_id)
    if retrieved:
        print(f"✓ الموظف: {retrieved.employee_id}")
        print(f"✓ الثقة: {retrieved.confidence:.1%}")
        print(f"✓ الجودة: {retrieved.quality_score:.1%}")
        print(f"✓ الوضوح: {retrieved.quality_details.sharpness:.1f}")
    
    # 4. إضافة لقائمة التأكيد
    print("\n📋 إضافة لقائمة التأكيد...")
    predictions = [
        {'employee_id': 'TEST001', 'name': 'موظف 1', 'confidence': 0.72},
        {'employee_id': 'TEST002', 'name': 'موظف 2', 'confidence': 0.68},
    ]
    queue_id = db.add_to_confirmation_queue(
        image_id=image_id,
        top_predictions=predictions,
        priority=2
    )
    print(f"✓ تم إضافة للقائمة: ID={queue_id}")
    
    # 5. الحصول على الإحصائيات
    print("\n📊 الإحصائيات:")
    stats = db.get_stats()
    print(f"✓ إجمالي الصور: {stats['images']['total']}")
    print(f"✓ الصور المؤكدة: {stats['images']['validated']}")
    print(f"✓ متوسط الجودة: {stats['images']['avg_quality']:.1%}")
    print(f"✓ متوسط الثقة: {stats['images']['avg_confidence']:.1%}")
    print(f"✓ قائمة التأكيد: {stats['queue']}")
    
    # 6. إغلاق
    print("\n🔒 إغلاق الاتصال...")
    db.close()
    print("✓ تم الإغلاق")
    
    print("\n" + "=" * 60)
    print("✅ كل الاختبارات نجحت!")
    print("=" * 60)
    print("\nقاعدة البيانات جاهزة في:")
    print(f"  {db.db_path.absolute()}")
    print("\nالخطوات التالية:")
    print("  1. python -m pytest tests/test_self_learning_db.py -v")
    print("  2. البدء في مُجمِّع البيانات (data_collector.py)")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ خطأ: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
