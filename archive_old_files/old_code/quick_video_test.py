"""
اختبار سريع لفيديو واحد - Quick Video Test
أداة مبسطة لاختبار إعدادات مختلفة على فيديو واحد
"""

import json
import time
import logging
from pathlib import Path

# إعداد السجلات
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def test_video_with_different_settings(video_path: str):
    """اختبار فيديو مع إعدادات مختلفة"""
    
    print("="*60)
    print("🎯 اختبار إعدادات مختلفة لكشف الأشخاص")
    print("="*60)
    print(f"📹 الفيديو: {video_path}")
    
    # الإعدادات المختلفة للاختبار
    test_configs = [
        {"name": "Default (Current)", "confidence": 0.35, "description": "الإعدادات الحالية"},
        {"name": "Strict", "confidence": 0.6, "description": "إعدادات صارمة - تقليل الكشوفات الخاطئة"},
        {"name": "Balanced", "confidence": 0.45, "description": "إعدادات متوازنة"},
        {"name": "Sensitive", "confidence": 0.25, "description": "إعدادات حساسة - كشف أكثر"}
    ]
    
    results = []
    
    for config in test_configs:
        print(f"\n🔧 اختبار: {config['name']}")
        print(f"   📝 الوصف: {config['description']}")
        print(f"   ⚙️ Confidence: {config['confidence']}")
        
        try:
            # تطبيق ضمان الاتساق
            from ensure_consistency import ensure_consistency
            ensure_consistency()
            
            # إنشاء المعالج مع الإعدادات الجديدة
            from src.level2_video_processor import Level2VideoProcessor
            
            processor = Level2VideoProcessor(
                device="cpu",
                imgsz=416,
                conf_threshold=config["confidence"],
                enable_face_recognition=False,  # تعطيل للسرعة
                enable_activity_recognition=False,  # تعطيل للسرعة
                enable_advanced_ai=False,  # تعطيل للسرعة
                random_seed=42
            )
            
            # معالجة الفيديو
            start_time = time.time()
            video_results = processor.process_video(
                input_path=video_path,
                output_path=None  # بدون حفظ للسرعة
            )
            processing_time = time.time() - start_time
            
            # تحليل النتائج
            detected_persons = len(video_results.get('statistics', []))
            
            result = {
                "config_name": config["name"],
                "confidence": config["confidence"],
                "detected_persons": detected_persons,
                "processing_time": processing_time,
                "description": config["description"]
            }
            
            results.append(result)
            
            print(f"   ✅ النتيجة: {detected_persons} أشخاص")
            print(f"   ⏱️ الوقت: {processing_time:.2f} ثانية")
            
        except Exception as e:
            print(f"   ❌ خطأ: {e}")
            results.append({
                "config_name": config["name"],
                "confidence": config["confidence"],
                "error": str(e)
            })
    
    # عرض الملخص
    print("\n" + "="*60)
    print("📊 ملخص النتائج")
    print("="*60)
    
    valid_results = [r for r in results if 'error' not in r]
    
    if valid_results:
        print("الإعداد                | الأشخاص | الوقت   | الوصف")
        print("-" * 60)
        
        for result in valid_results:
            name = result["config_name"][:20].ljust(20)
            persons = str(result["detected_persons"]).center(8)
            time_str = f"{result['processing_time']:.2f}s".center(8)
            desc = result["description"][:25]
            print(f"{name} | {persons} | {time_str} | {desc}")
        
        # إيجاد أفضل إعداد
        person_counts = [r["detected_persons"] for r in valid_results]
        unique_counts = list(set(person_counts))
        
        print(f"\n📈 تحليل النتائج:")
        print(f"   • أقل عدد: {min(person_counts)} أشخاص")
        print(f"   • أكثر عدد: {max(person_counts)} أشخاص")
        print(f"   • عدد النتائج المختلفة: {len(unique_counts)}")
        
        # توصيات
        print(f"\n💡 التوصيات:")
        
        if len(unique_counts) == 1:
            print("   ✅ جميع الإعدادات تعطي نفس النتيجة - النظام مستقر")
        elif max(person_counts) > min(person_counts) * 2:
            print("   ⚠️ يوجد اختلاف كبير في النتائج:")
            print("   • جرب زيادة confidence إلى 0.5 أو أعلى")
            print("   • تحقق من جودة الفيديو")
            print("   • قد تحتاج لضبط إعدادات التتبع")
        else:
            print("   📊 الاختلاف طبيعي - اختر الإعداد المناسب لاحتياجاتك")
        
        # أفضل إعداد للدقة
        if max(person_counts) > 0:
            # إذا كان هناك كشوفات، اختر الإعداد الأكثر توازناً
            balanced_results = [r for r in valid_results if r["detected_persons"] > 0]
            if balanced_results:
                # اختر الإعداد بأعلى confidence من الذين كشفوا أشخاص
                best_result = max(balanced_results, key=lambda x: x["confidence"])
                print(f"\n🏆 الإعداد المقترح: {best_result['config_name']}")
                print(f"   • Confidence: {best_result['confidence']}")
                print(f"   • النتيجة: {best_result['detected_persons']} أشخاص")
        
    else:
        print("❌ لم تنجح أي من الإعدادات")
    
    # حفظ النتائج
    results_file = Path("video_test_results.json")
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            "video_path": video_path,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 تم حفظ النتائج في: {results_file}")
    
    return results

def apply_best_settings(confidence: float):
    """تطبيق أفضل إعدادات على النظام"""
    config_file = Path("config/unified_config.json")
    
    try:
        # قراءة الإعدادات الحالية
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # نسخ احتياطي
        backup_file = Path("config/unified_config_backup.json")
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        # تطبيق الإعدادات الجديدة
        config["yolo"]["confidence"] = confidence
        config["level2_processor"]["conf_threshold"] = confidence
        
        # إعدادات تتبع محسنة
        config["tracking"]["track_high_thresh"] = min(0.7, confidence + 0.1)
        config["tracking"]["new_track_thresh"] = min(0.8, confidence + 0.2)
        config["tracking"]["match_thresh"] = 0.85
        
        # حفظ الإعدادات الجديدة
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ تم تطبيق الإعدادات الجديدة:")
        print(f"   • Confidence: {confidence}")
        print(f"   • Track High Thresh: {config['tracking']['track_high_thresh']}")
        print(f"   • New Track Thresh: {config['tracking']['new_track_thresh']}")
        print(f"   • نسخة احتياطية: {backup_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في تطبيق الإعدادات: {e}")
        return False

def main():
    """الدالة الرئيسية"""
    import sys
    
    if len(sys.argv) < 2:
        # استخدام الفيديو التجريبي
        video_path = "web_app/static/uploads/test_videos/test_sample.mp4"
        print("Using test video...")
    else:
        video_path = sys.argv[1]
    
    # التحقق من وجود الفيديو
    if not Path(video_path).exists():
        print(f"❌ الفيديو غير موجود: {video_path}")
        return
    
    # اختبار الإعدادات
    results = test_video_with_different_settings(video_path)
    
    # سؤال المستخدم عن تطبيق الإعدادات
    valid_results = [r for r in results if 'error' not in r and r['detected_persons'] > 0]
    
    if valid_results:
        print(f"\n❓ هل تريد تطبيق إعدادات محسنة على النظام؟")
        
        # اقتراح أفضل confidence
        best_confidence = max(valid_results, key=lambda x: x["confidence"])["confidence"]
        print(f"   الإعداد المقترح: Confidence = {best_confidence}")
        
        choice = input("   اكتب 'y' للموافقة أو أي شيء آخر للإلغاء: ").lower().strip()
        
        if choice in ['y', 'yes', 'نعم']:
            if apply_best_settings(best_confidence):
                print("\n🎉 تم تطبيق الإعدادات بنجاح!")
                print("🔄 أعد تشغيل النظام لتفعيل الإعدادات الجديدة")
            else:
                print("\n❌ فشل في تطبيق الإعدادات")
        else:
            print("\n📝 لم يتم تطبيق الإعدادات")
    
    print(f"\n🎯 انتهى الاختبار!")

if __name__ == "__main__":
    main()
