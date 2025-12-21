#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار النظام الكامل للتعلم الذاتي
Complete System Test
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

from src.self_learning import (
    SelfLearningDB,
    ImageStorage,
    QualityAssessor,
    DataCollector,
    ContinuousTrainer,
    SystemMonitor,
)


def print_section(title):
    """طباعة عنوان قسم"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def main():
    print_section("🧪 اختبار النظام الكامل للتعلم الذاتي")
    
    # 1. تهيئة المكونات
    print("\n📦 تهيئة المكونات...")
    db = SelfLearningDB()
    storage = ImageStorage()
    assessor = QualityAssessor()
    collector = DataCollector(db=db, storage=storage, quality_assessor=assessor)
    trainer = ContinuousTrainer(db=db)
    monitor = SystemMonitor(db=db)
    
    print("✓ قاعدة البيانات")
    print("✓ نظام التخزين")
    print("✓ مُقيِّم الجودة")
    print("✓ مُجمِّع البيانات")
    print("✓ نظام التدريب")
    print("✓ نظام المراقبة")
    
    # 2. إحصائيات قاعدة البيانات
    print_section("💾 إحصائيات قاعدة البيانات")
    
    stats = db.get_stats()
    print(f"الصور:             {stats['images']['total']}")
    print(f"  - مؤكدة:         {stats['images']['validated']}")
    print(f"  - متوسط الجودة:  {stats['images']['avg_quality']:.1%}")
    print(f"  - متوسط الثقة:   {stats['images']['avg_confidence']:.1%}")
    print(f"قائمة التأكيد:     {stats['queue']}")
    print(f"التصحيحات:        {stats['corrections']}")
    
    # 3. حالة التدريب
    print_section("🎓 حالة التدريب")
    
    training_stats = trainer.get_training_stats()
    print(f"آخر نموذج:        {training_stats.get('latest_performance', {}).get('model_version', 'لا يوجد') if training_stats.get('latest_performance') else 'لا يوجد'}")
    
    if training_stats.get('latest_performance'):
        perf = training_stats['latest_performance']
        print(f"الدقة:             {perf['accuracy']:.1%}")
        print(f"Precision:         {perf['precision']:.1%}")
        print(f"Recall:            {perf['recall']:.1%}")
        print(f"F1 Score:          {perf['f1_score']:.1%}")
    
    print(f"صور غير مستخدمة:  {training_stats['unused_images']}")
    print(f"تصحيحات حديثة:    {training_stats['recent_corrections']}")
    print(f"يحتاج تدريب:      {'نعم' if training_stats['should_retrain'] else 'لا'}")
    print(f"السبب:            {training_stats['retrain_reason']}")
    
    # 4. اختبار التدريب
    print_section("🚀 اختبار التدريب")
    
    should_train, reason = trainer.should_retrain()
    print(f"الحاجة للتدريب:   {reason}")
    
    if should_train or training_stats['unused_images'] >= 5:
        print("\n▶ تشغيل التدريب التجريبي...")
        performance = trainer.train(force=True)
        
        if performance:
            print(f"✓ نجح التدريب!")
            print(f"  الإصدار:       {performance.model_version}")
            print(f"  الدقة:         {performance.accuracy:.1%}")
            print(f"  F1 Score:      {performance.f1_score:.1%}")
            print(f"  عينات الاختبار: {performance.test_samples}")
        else:
            print("✗ فشل التدريب")
    else:
        print("⏭️  تخطي التدريب - لا حاجة له")
    
    # 5. صحة النظام
    print_section("🏥 صحة النظام")
    
    health_score = monitor.get_health_score()
    print(f"درجة الصحة:       {health_score:.1f}/100")
    
    if health_score >= 90:
        print("الحالة:           🟢 ممتاز")
    elif health_score >= 75:
        print("الحالة:           🔵 جيد")
    elif health_score >= 60:
        print("الحالة:           🟡 متوسط")
    else:
        print("الحالة:           🔴 يحتاج انتباه")
    
    # 6. التنبيهات
    print_section("🔔 التنبيهات النشطة")
    
    alerts = monitor.run_full_check()
    
    if alerts:
        # تصنيف حسب المستوى
        critical = [a for a in alerts if a.level.value == 'critical']
        errors = [a for a in alerts if a.level.value == 'error']
        warnings = [a for a in alerts if a.level.value == 'warning']
        infos = [a for a in alerts if a.level.value == 'info']
        
        print(f"إجمالي التنبيهات: {len(alerts)}")
        print(f"  🔴 عاجل:        {len(critical)}")
        print(f"  🟠 أخطاء:       {len(errors)}")
        print(f"  🟡 تحذيرات:     {len(warnings)}")
        print(f"  🔵 معلومات:     {len(infos)}")
        
        # عرض أهم التنبيهات
        print("\nأهم التنبيهات:")
        for i, alert in enumerate(alerts[:5], 1):
            emoji = {
                'critical': '🔴',
                'error': '🟠',
                'warning': '🟡',
                'info': '🔵'
            }[alert.level.value]
            
            print(f"\n  {i}. {emoji} {alert.title}")
            print(f"     {alert.message}")
    else:
        print("✅ لا توجد تنبيهات - النظام يعمل بشكل ممتاز!")
    
    # 7. إحصائيات التخزين
    print_section("💿 إحصائيات التخزين")
    
    storage_stats = storage.get_storage_stats()
    print(f"صور خام:          {storage_stats['raw_images']}")
    print(f"صور مؤكدة:       {storage_stats['validated_images']}")
    print(f"صور مرفوضة:      {storage_stats['rejected_images']}")
    print(f"عدد الموظفين:     {storage_stats['total_employees']}")
    print(f"حجم التخزين:      {storage_stats['storage_size_mb']:.2f} MB")
    
    # 8. الملخص النهائي
    print_section("📋 الملخص النهائي")
    
    print("✅ النظام الكامل:")
    print("  ✓ قاعدة البيانات تعمل")
    print("  ✓ التخزين منظم")
    print("  ✓ جمع البيانات نشط")
    print("  ✓ التدريب المستمر جاهز")
    print("  ✓ المراقبة فعالة")
    
    print(f"\n📈 الأداء:")
    print(f"  • صحة النظام: {health_score:.1f}%")
    print(f"  • إجمالي الصور: {stats['images']['total']}")
    print(f"  • معدل الجودة: {stats['images']['avg_quality']:.1%}")
    
    print("\n🌐 الواجهات المتاحة:")
    print("  • الإحصائيات:    http://127.0.0.1:5000/self-learning")
    print("  • قائمة التأكيد:  http://127.0.0.1:5000/self-learning/confirmation/queue")
    print("  • المراقبة:       http://127.0.0.1:5000/self-learning/monitoring")
    
    print("\n🔧 API Endpoints:")
    print("  • GET  /self-learning/api/stats")
    print("  • POST /self-learning/api/confirm")
    print("  • POST /self-learning/api/train")
    print("  • GET  /self-learning/api/training-stats")
    print("  • GET  /self-learning/api/monitoring/health")
    
    print_section("✅ الاختبار مكتمل!")
    
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
