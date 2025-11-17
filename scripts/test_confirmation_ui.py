#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار واجهة التأكيد البشري
Test Confirmation UI
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
)


def create_test_face(emp_id, quality='good'):
    """إنشاء وجه تجريبي"""
    # صورة 200x200
    if quality == 'good':
        img = np.random.randint(100, 200, (200, 200, 3), dtype=np.uint8)
        # إضافة نص
        cv2.putText(img, emp_id, (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.8, (255, 255, 255), 2)
    else:
        img = np.random.randint(50, 150, (200, 200, 3), dtype=np.uint8)
    
    return img


def main():
    print("=" * 70)
    print("🧪 اختبار واجهة التأكيد البشري")
    print("=" * 70)
    
    # 1. تهيئة
    print("\n📦 تهيئة النظام...")
    db = SelfLearningDB()
    storage = ImageStorage()
    assessor = QualityAssessor()
    collector = DataCollector(
        db=db, 
        storage=storage, 
        quality_assessor=assessor,
        min_confidence=0.70  # تخفيض لإضافة حالات مشكوك فيها
    )
    
    # 2. إضافة حالات تجريبية متنوعة
    print("\n📸 إضافة حالات تجريبية...")
    print("-" * 70)
    
    test_cases = [
        # (emp_id, confidence, quality, description)
        ('EMP101', 0.92, 'good', 'حالة واضحة - ثقة عالية'),
        ('EMP102', 0.78, 'good', 'حالة مشكوك فيها - ثقة متوسطة'),
        ('EMP103', 0.73, 'good', 'حالة حدية - قريبة من الحد'),
        ('EMP104', 0.88, 'good', 'حالة جيدة'),
        ('EMP105', 0.75, 'good', 'حالة تحتاج تأكيد'),
    ]
    
    collected_count = 0
    
    for emp_id, confidence, quality, description in test_cases:
        print(f"\n{description}:")
        print(f"  الموظف: {emp_id} | الثقة: {confidence:.1%}")
        
        # إنشاء إطار تجريبي
        frame = np.random.randint(80, 180, (480, 640, 3), dtype=np.uint8)
        
        # إضافة وجه تجريبي
        face_img = create_test_face(emp_id, quality)
        frame[140:340, 220:420] = face_img
        
        bbox = (220, 140, 420, 340)
        
        # التوقعات (للتعلم النشط)
        predictions = [
            {'employee_id': emp_id, 'name': f'موظف {emp_id}', 'confidence': confidence},
            {'employee_id': f'{emp_id}X', 'name': f'موظف بديل', 'confidence': confidence - 0.12},
            {'employee_id': 'UNKNOWN', 'name': 'غير معروف', 'confidence': confidence - 0.25},
        ]
        
        # محاولة الجمع
        image_id = collector.collect_face(
            frame=frame,
            employee_id=emp_id,
            confidence=confidence,
            bbox=bbox,
            predictions=predictions,
            metadata={'camera': 'test_cam', 'location': 'entrance', 'test': True}
        )
        
        if image_id:
            print(f"  ✅ تم الجمع: صورة #{image_id}")
            collected_count += 1
        else:
            print(f"  ❌ تم الرفض")
    
    print(f"\nتم جمع {collected_count} من {len(test_cases)} حالة")
    
    # 3. عرض الإحصائيات
    print("\n\n📊 إحصائيات قاعدة البيانات:")
    print("-" * 70)
    
    stats = db.get_stats()
    print(f"إجمالي الصور:        {stats['images']['total']}")
    print(f"الصور المؤكدة:       {stats['images']['validated']}")
    print(f"متوسط الجودة:        {stats['images']['avg_quality']:.1%}")
    print(f"متوسط الثقة:         {stats['images']['avg_confidence']:.1%}")
    
    queue_stats = stats.get('queue', {})
    print(f"\nقائمة التأكيد:")
    print(f"  معلقة:             {queue_stats.get('pending', 0)}")
    print(f"  مؤكدة:            {queue_stats.get('confirmed', 0)}")
    print(f"  مرفوضة:           {queue_stats.get('rejected', 0)}")
    
    # 4. عرض قائمة التأكيد
    print("\n\n📋 معاينة قائمة التأكيد:")
    print("-" * 70)
    
    pending = db.get_pending_confirmations(limit=10)
    if pending:
        for i, item in enumerate(pending, 1):
            img = db.get_training_image(item.image_id)
            if img:
                print(f"\n{i}. صورة #{item.image_id} | أولوية {item.priority}")
                print(f"   الموظف المتوقع: {img.employee_id}")
                print(f"   الثقة: {img.confidence:.1%} | الجودة: {img.quality_score:.1%}")
                print(f"   عدد التوقعات: {len(item.top_predictions)}")
                
                if item.top_predictions:
                    print(f"   أفضل 2:")
                    for j, pred in enumerate(item.top_predictions[:2], 1):
                        print(f"     {j}. {pred.get('employee_id')} - {pred.get('confidence', 0):.1%}")
    else:
        print("لا توجد حالات معلقة")
    
    # 5. التعليمات
    print("\n" + "=" * 70)
    print("✅ تم تجهيز البيانات التجريبية!")
    print("=" * 70)
    
    print("\n🌐 افتح المتصفح:")
    print("  1. صفحة الإحصائيات: http://127.0.0.1:5000/self-learning")
    print("  2. قائمة التأكيد:   http://127.0.0.1:5000/self-learning/confirmation/queue")
    
    print("\n📝 ما يمكنك فعله:")
    print("  • عرض كل الصور المعلقة")
    print("  • تأكيد التوقعات الصحيحة")
    print("  • رفض الصور الخاطئة")
    print("  • تصحيح التوقعات الخاطئة")
    print("  • فلترة حسب الأولوية")
    
    print("\n💡 نصائح:")
    print("  • الأولوية 1-3 = عاجل (أحمر)")
    print("  • الأولوية 4-6 = متوسط (أصفر)")
    print("  • الأولوية 7-10 = عادي (أزرق)")
    
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
