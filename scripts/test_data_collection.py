#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار نظام جمع البيانات
Test Data Collection System
"""
import sys
import io
from pathlib import Path

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import cv2
import numpy as np
from datetime import datetime

from src.self_learning import (
    SelfLearningDB,
    ImageStorage,
    QualityAssessor,
    DataCollector,
    CollectionPolicy
)


def create_test_image(quality='good'):
    """إنشاء صورة تجريبية
    
    Args:
        quality: 'good', 'bad', 'blurry'
    """
    # صورة 200x200
    if quality == 'good':
        # صورة جيدة مع نمط واضح
        img = np.random.randint(100, 200, (200, 200, 3), dtype=np.uint8)
        # إضافة نمط لزيادة الوضوح
        for i in range(0, 200, 10):
            cv2.line(img, (i, 0), (i, 200), (255, 255, 255), 1)
    
    elif quality == 'bad':
        # صورة مظلمة
        img = np.random.randint(0, 50, (200, 200, 3), dtype=np.uint8)
    
    elif quality == 'blurry':
        # صورة ضبابية
        img = np.random.randint(100, 200, (200, 200, 3), dtype=np.uint8)
        img = cv2.GaussianBlur(img, (21, 21), 0)
    
    else:
        img = np.random.randint(100, 200, (200, 200, 3), dtype=np.uint8)
    
    return img


def main():
    print("=" * 70)
    print("🧪 اختبار نظام جمع البيانات التلقائي")
    print("=" * 70)
    
    # 1. تهيئة المكونات
    print("\n📦 تهيئة المكونات...")
    db = SelfLearningDB()
    storage = ImageStorage()
    assessor = QualityAssessor()
    collector = DataCollector(db=db, storage=storage, quality_assessor=assessor)
    policy = CollectionPolicy(min_interval_seconds=1, max_images_per_session=5)
    
    print(f"✓ قاعدة البيانات: {db.db_path}")
    print(f"✓ التخزين: {storage.base_path}")
    
    # 2. اختبار تقييم الجودة
    print("\n📊 اختبار تقييم الجودة...")
    print("-" * 70)
    
    for quality_type in ['good', 'bad', 'blurry']:
        img = create_test_image(quality_type)
        metrics = assessor.assess_image(img)
        acceptable = assessor.is_acceptable(metrics)
        
        print(f"\n{quality_type.upper():10} | "
              f"وضوح: {metrics.sharpness:6.1f} | "
              f"إضاءة: {metrics.brightness:6.1f} | "
              f"درجة: {metrics.overall_score:.1%} | "
              f"{'✅ مقبول' if acceptable else '❌ مرفوض'}")
        
        if not acceptable:
            reasons = assessor.get_rejection_reasons(metrics)
            print(f"           الأسباب: {', '.join(reasons)}")
    
    # 3. اختبار جمع البيانات
    print("\n\n📸 اختبار جمع البيانات...")
    print("-" * 70)
    
    test_scenarios = [
        ('EMP001', 0.95, 'good', "ثقة عالية + جودة جيدة"),
        ('EMP002', 0.88, 'good', "ثقة متوسطة + جودة جيدة"),
        ('EMP003', 0.75, 'good', "ثقة منخفضة + جودة جيدة"),
        ('EMP004', 0.92, 'bad', "ثقة عالية + جودة سيئة"),
        ('EMP005', 0.65, 'blurry', "ثقة منخفضة + جودة ضبابية"),
    ]
    
    for emp_id, confidence, quality, description in test_scenarios:
        print(f"\n{description}:")
        print(f"  الموظف: {emp_id} | الثقة: {confidence:.1%} | الجودة: {quality}")
        
        # إنشاء إطار تجريبي
        frame = np.random.randint(100, 200, (480, 640, 3), dtype=np.uint8)
        
        # إنشاء وجه تجريبي في المنتصف
        face_img = create_test_image(quality)
        frame[140:340, 220:420] = face_img
        
        bbox = (220, 140, 420, 340)
        
        # محاولة الجمع
        if policy.can_collect(emp_id):
            predictions = [
                {'employee_id': emp_id, 'name': f'موظف {emp_id}', 'confidence': confidence},
                {'employee_id': 'OTHER', 'name': 'آخر', 'confidence': confidence - 0.10},
            ]
            
            image_id = collector.collect_face(
                frame=frame,
                employee_id=emp_id,
                confidence=confidence,
                bbox=bbox,
                predictions=predictions,
                metadata={'camera': 'test_cam', 'test': True}
            )
            
            if image_id:
                print(f"  ✅ تم الجمع بنجاح: صورة #{image_id}")
                policy.mark_collected(emp_id)
            else:
                print(f"  ❌ تم رفض الصورة")
        else:
            print(f"  ⏸️  تم تخطي (سياسة الجمع)")
    
    # 4. الإحصائيات
    print("\n\n📊 إحصائيات الجلسة:")
    print("-" * 70)
    
    session_stats = collector.get_session_stats()
    print(f"المحاولات الكلية:    {session_stats['total_attempts']}")
    print(f"تم الجمع:            {session_stats['collected']}")
    print(f"مرفوض (جودة):        {session_stats['rejected_quality']}")
    print(f"مرفوض (ثقة):         {session_stats['rejected_confidence']}")
    print(f"مرفوض (حصة):         {session_stats['rejected_quota']}")
    print(f"نسبة النجاح:         {session_stats['success_rate']:.1f}%")
    
    # 5. إحصائيات قاعدة البيانات
    print("\n\n💾 إحصائيات قاعدة البيانات:")
    print("-" * 70)
    
    db_stats = db.get_stats()
    print(f"إجمالي الصور:        {db_stats['images']['total']}")
    print(f"الصور المؤكدة:       {db_stats['images']['validated']}")
    print(f"متوسط الجودة:        {db_stats['images']['avg_quality']:.1%}")
    print(f"متوسط الثقة:         {db_stats['images']['avg_confidence']:.1%}")
    print(f"قائمة التأكيد:       {db_stats['queue']}")
    print(f"التصحيحات:          {db_stats['corrections']}")
    
    # 6. إحصائيات التخزين
    print("\n\n💿 إحصائيات التخزين:")
    print("-" * 70)
    
    storage_stats = storage.get_storage_stats()
    print(f"صور خام:             {storage_stats['raw_images']}")
    print(f"صور مؤكدة:          {storage_stats['validated_images']}")
    print(f"صور مرفوضة:         {storage_stats['rejected_images']}")
    print(f"عدد الموظفين:        {storage_stats['total_employees']}")
    print(f"حجم التخزين:         {storage_stats['storage_size_mb']} MB")
    
    # 7. عرض قائمة التأكيد
    print("\n\n📋 قائمة التأكيد:")
    print("-" * 70)
    
    pending = db.get_pending_confirmations(limit=10)
    if pending:
        for item in pending:
            img = db.get_training_image(item.image_id)
            if img:
                print(f"\nصورة #{item.image_id} | أولوية {item.priority}")
                print(f"  الموظف: {img.employee_id} | الثقة: {img.confidence:.1%}")
                print(f"  التوقعات: {len(item.top_predictions)} خيارات")
    else:
        print("لا توجد حالات معلقة")
    
    # 8. الخلاصة
    print("\n" + "=" * 70)
    print("✅ اكتمل الاختبار بنجاح!")
    print("=" * 70)
    
    print("\n📂 المسارات:")
    print(f"  قاعدة البيانات: {db.db_path.absolute()}")
    print(f"  الصور المخزنة:   {storage.base_path.absolute()}")
    
    print("\n🔗 الخطوات التالية:")
    print("  1. افتح واجهة التعلم الذاتي: http://127.0.0.1:5000/self-learning")
    print("  2. راجع الصور في المجلد: training_data/raw/")
    print("  3. ابدأ التكامل مع نظام التعرف على الوجوه")
    
    # إغلاق
    db.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ خطأ: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
