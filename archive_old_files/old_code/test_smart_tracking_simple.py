"""
اختبار بسيط لنظام التتبع الذكي
Simple Test for Smart Tracking System
"""

import sys
import json
from pathlib import Path

# إضافة المسار للاستيراد
sys.path.append(str(Path(__file__).parent))

try:
    from smart_person_tracker import SmartPersonTracker
    print("تم استيراد نظام التتبع الذكي بنجاح")
    
    # إنشاء مثيل للاختبار
    tracker = SmartPersonTracker(max_persons=10, similarity_threshold=0.7)
    
    print("الميزات المتاحة:")
    print("- تتبع ذكي للأشخاص")
    print("- إعادة التعرف عند العودة للكادر") 
    print("- عدد دقيق للأشخاص")
    print("- تتبع الأنشطة (عمل، نوم، موبايل)")
    print("- منع الكشوفات الخاطئة")
    
    # اختبار الوظائف الأساسية
    print(f"\nعدد الأشخاص النشطين: {tracker.get_active_persons_count()}")
    
    stats = tracker.get_tracking_stats()
    print(f"إحصائيات التتبع: {stats}")
    
    print("\nنظام التتبع الذكي جاهز للاستخدام!")
    
except ImportError as e:
    print(f"خطأ في الاستيراد: {e}")
    print("تأكد من وجود المكتبات المطلوبة")

except Exception as e:
    print(f"خطأ عام: {e}")

# اختبار قراءة الإعدادات
try:
    config_file = Path("config/unified_config.json")
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        smart_config = config.get('smart_tracking', {})
        if smart_config.get('enabled', False):
            print(f"\nإعدادات التتبع الذكي:")
            print(f"- الحد الأقصى للأشخاص: {smart_config.get('max_persons', 15)}")
            print(f"- عتبة التشابه: {smart_config.get('similarity_threshold', 0.7)}")
            print(f"- وقت فقدان التتبع: {smart_config.get('max_lost_time', 30)} ثانية")
        else:
            print("التتبع الذكي غير مفعل في الإعدادات")
    else:
        print("ملف الإعدادات غير موجود")

except Exception as e:
    print(f"خطأ في قراءة الإعدادات: {e}")

print("\nلتطبيق التتبع الذكي:")
print("1. أعد تشغيل الخادم")
print("2. جرب معالجة فيديو")
print("3. راقب تحسن دقة العدد")
