"""
اختبار توحيد النتائج بين أعضاء الفريق
Test Consistency Across Team Members
"""
import json
import hashlib
import argparse
import sys
from pathlib import Path
from datetime import datetime
import logging

# إعداد السجلات
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("consistency_test")

def test_consistency(video_path, output_dir="consistency_test_results", team_member_name="unknown"):
    """
    اختبار الاتساق في النتائج لعضو في الفريق
    """
    logger.info(f"🧪 بدء اختبار الاتساق لـ: {team_member_name}")
    
    # التأكد من وجود الفيديو
    video_path = Path(video_path)
    if not video_path.exists():
        logger.error(f"❌ الفيديو غير موجود: {video_path}")
        return None
    
    # إنشاء مجلد النتائج
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # ضمان الاتساق أولاً
        from ensure_consistency import ensure_consistency, get_system_fingerprint
        config = ensure_consistency()
        
        # الحصول على بصمة النظام
        system_fingerprint = get_system_fingerprint()
        
        # تشغيل المعالج
        logger.info("🎬 بدء معالجة الفيديو...")
        results = run_video_processing(video_path, config)
        
        # حساب hash للنتائج
        results_hash = calculate_results_hash(results)
        
        # إنشاء تقرير شامل
        test_report = {
            "test_info": {
                "team_member": team_member_name,
                "timestamp": datetime.now().isoformat(),
                "video_path": str(video_path),
                "video_size": video_path.stat().st_size,
                "video_hash": calculate_file_hash(video_path)
            },
            "system_info": system_fingerprint,
            "config_used": config,
            "results": results,
            "results_hash": results_hash,
            "consistency_markers": generate_consistency_markers(results)
        }
        
        # حفظ التقرير
        report_filename = f"consistency_test_{team_member_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = output_dir / report_filename
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(test_report, f, indent=2, ensure_ascii=False)
        
        # طباعة النتائج
        print_test_results(test_report, report_path)
        
        return test_report
        
    except Exception as e:
        logger.error(f"❌ خطأ في اختبار الاتساق: {e}")
        return None

def run_video_processing(video_path, config):
    """تشغيل معالجة الفيديو مع الإعدادات الموحدة"""
    try:
        from src.level2_video_processor import Level2VideoProcessor
        
        # إنشاء المعالج بالإعدادات الموحدة
        processor = Level2VideoProcessor(
            device=config["yolo"]["device"],
            imgsz=config["yolo"]["imgsz"],
            conf_threshold=config["level2_processor"]["conf_threshold"],
            enable_advanced_ai=config["level2_processor"]["enable_advanced_ai"],
            enable_face_recognition=config["level2_processor"]["enable_face_recognition"],
            enable_activity_recognition=config["level2_processor"]["enable_activity_recognition"],
            yolo_model=config["level2_processor"]["yolo_model"],
            activity_window=config["level2_processor"]["activity_window"]
        )
        
        # معالجة الفيديو
        output_path = f"consistency_test_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        
        results = processor.process_video(
            input_path=str(video_path),
            output_path=output_path,
            frame_skip=config["level2_processor"]["frame_skip"],
            max_duration=60,  # حد أقصى دقيقة واحدة للاختبار
            task_id="consistency_test"
        )
        
        return results
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة الفيديو: {e}")
        raise

def calculate_results_hash(results):
    """حساب hash للنتائج للتحقق من التطابق"""
    try:
        # تحويل النتائج لنص مرتب (مع تجاهل الطوابع الزمنية المتغيرة)
        results_copy = clean_results_for_hashing(results)
        results_str = json.dumps(results_copy, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(results_str.encode('utf-8')).hexdigest()
    except Exception as e:
        logger.warning(f"⚠️ لم يتمكن من حساب hash النتائج: {e}")
        return "hash_calculation_failed"

def clean_results_for_hashing(results):
    """تنظيف النتائج من البيانات المتغيرة للحصول على hash متسق"""
    if not isinstance(results, dict):
        return results
    
    cleaned = {}
    
    # قائمة المفاتيح التي يجب تجاهلها في الـ hash
    ignore_keys = [
        'processing_time', 'timestamp', 'start_time', 'end_time',
        'file_path', 'output_path', 'task_id', 'frame_timestamps'
    ]
    
    for key, value in results.items():
        if key in ignore_keys:
            continue
            
        if isinstance(value, dict):
            cleaned[key] = clean_results_for_hashing(value)
        elif isinstance(value, list):
            cleaned[key] = [clean_results_for_hashing(item) if isinstance(item, dict) else item for item in value]
        elif isinstance(value, float):
            # تقريب الأرقام العشرية لتجنب اختلافات الدقة
            cleaned[key] = round(value, 6)
        else:
            cleaned[key] = value
    
    return cleaned

def calculate_file_hash(file_path):
    """حساب hash للملف"""
    try:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.warning(f"⚠️ لم يتمكن من حساب hash الملف: {e}")
        return "file_hash_failed"

def generate_consistency_markers(results):
    """إنشاء علامات الاتساق للمقارنة السريعة"""
    markers = {}
    
    try:
        if isinstance(results, dict):
            # عدد الأشخاص المكتشفين
            if 'statistics' in results and isinstance(results['statistics'], list):
                markers['total_persons'] = len(results['statistics'])
                
                # مجموع أوقات العمل
                total_working_time = sum(
                    person.get('working_duration', 0) 
                    for person in results['statistics']
                )
                markers['total_working_time'] = round(total_working_time, 2)
                
                # عدد الأنشطة المكتشفة
                total_activities = sum(
                    len(person.get('activities', {})) 
                    for person in results['statistics']
                )
                markers['total_activities'] = total_activities
            
            # معلومات الفيديو
            if 'video_info' in results:
                video_info = results['video_info']
                markers['video_duration'] = video_info.get('duration_sec', 0)
                markers['total_frames'] = video_info.get('total_frames', 0)
                markers['fps'] = video_info.get('fps', 0)
            
            # رؤى الذكاء الاصطناعي
            if 'ai_insights' in results:
                ai_insights = results['ai_insights']
                markers['anomalies_detected'] = len(ai_insights.get('anomalies', []))
                markers['high_risk_persons'] = len([
                    p for p in results.get('statistics', [])
                    if p.get('risk_level') == 'high'
                ])
    
    except Exception as e:
        logger.warning(f"⚠️ خطأ في إنشاء علامات الاتساق: {e}")
        markers['error'] = str(e)
    
    return markers

def print_test_results(test_report, report_path):
    """طباعة نتائج الاختبار"""
    print("\n" + "="*60)
    print("🧪 نتائج اختبار الاتساق")
    print("="*60)
    
    # معلومات الاختبار
    test_info = test_report['test_info']
    print(f"👤 عضو الفريق: {test_info['team_member']}")
    print(f"🕒 وقت الاختبار: {test_info['timestamp']}")
    print(f"📹 الفيديو: {test_info['video_path']}")
    print(f"📊 حجم الفيديو: {test_info['video_size']} بايت")
    print(f"🔍 Hash الفيديو: {test_info['video_hash'][:16]}...")
    
    # معلومات النظام
    system_info = test_report['system_info']
    print(f"\n💻 معلومات النظام:")
    print(f"  Python: {system_info['python_version']}")
    print(f"  Platform: {system_info['platform']}")
    print(f"  PyTorch: {system_info['torch_version']}")
    print(f"  CUDA: {system_info['cuda_available']}")
    
    # علامات الاتساق
    markers = test_report['consistency_markers']
    print(f"\n📋 علامات الاتساق:")
    for key, value in markers.items():
        print(f"  {key}: {value}")
    
    # Hash النتائج
    print(f"\n🔍 Hash النتائج: {test_report['results_hash']}")
    print(f"📄 تقرير مفصل: {report_path}")
    
    print("\n✅ تم حفظ نتائج الاختبار بنجاح!")
    print("📤 شارك هذا الملف مع الفريق للمقارنة")

def compare_test_results(report1_path, report2_path):
    """مقارنة نتائج اختبارين من عضوين مختلفين"""
    try:
        # تحميل التقارير
        with open(report1_path, 'r', encoding='utf-8') as f:
            report1 = json.load(f)
        
        with open(report2_path, 'r', encoding='utf-8') as f:
            report2 = json.load(f)
        
        print("\n" + "="*60)
        print("🔍 مقارنة نتائج الاتساق")
        print("="*60)
        
        # مقارنة المعلومات الأساسية
        member1 = report1['test_info']['team_member']
        member2 = report2['test_info']['team_member']
        print(f"👥 المقارنة بين: {member1} و {member2}")
        
        # مقارنة hash النتائج
        hash1 = report1['results_hash']
        hash2 = report2['results_hash']
        
        if hash1 == hash2:
            print("✅ النتائج متطابقة تماماً!")
        else:
            print("❌ النتائج مختلفة!")
            print(f"  Hash {member1}: {hash1}")
            print(f"  Hash {member2}: {hash2}")
        
        # مقارنة علامات الاتساق
        markers1 = report1['consistency_markers']
        markers2 = report2['consistency_markers']
        
        print(f"\n📊 مقارنة علامات الاتساق:")
        differences = []
        
        all_keys = set(markers1.keys()) | set(markers2.keys())
        for key in sorted(all_keys):
            val1 = markers1.get(key, "غير موجود")
            val2 = markers2.get(key, "غير موجود")
            
            if val1 == val2:
                print(f"  ✅ {key}: {val1}")
            else:
                print(f"  ❌ {key}: {val1} != {val2}")
                differences.append(key)
        
        # مقارنة إعدادات النظام
        sys1 = report1['system_info']
        sys2 = report2['system_info']
        
        print(f"\n🖥️ مقارنة إعدادات النظام:")
        system_differences = []
        
        for key in ['python_version', 'torch_version', 'numpy_version']:
            if key in sys1 and key in sys2:
                if sys1[key] == sys2[key]:
                    print(f"  ✅ {key}: {sys1[key]}")
                else:
                    print(f"  ❌ {key}: {sys1[key]} != {sys2[key]}")
                    system_differences.append(key)
        
        # الخلاصة
        print(f"\n📋 الخلاصة:")
        if not differences and not system_differences:
            print("🎉 النظامان متطابقان تماماً!")
        else:
            print("⚠️ هناك اختلافات تحتاج للمراجعة:")
            if differences:
                print(f"  - اختلافات في النتائج: {', '.join(differences)}")
            if system_differences:
                print(f"  - اختلافات في النظام: {', '.join(system_differences)}")
        
        return hash1 == hash2
        
    except Exception as e:
        logger.error(f"❌ خطأ في مقارنة النتائج: {e}")
        return False

def main():
    """الدالة الرئيسية"""
    parser = argparse.ArgumentParser(description="اختبار اتساق النتائج بين أعضاء الفريق")
    parser.add_argument("--video", required=True, help="مسار الفيديو للاختبار")
    parser.add_argument("--name", required=True, help="اسم عضو الفريق")
    parser.add_argument("--output", default="consistency_test_results", help="مجلد النتائج")
    parser.add_argument("--compare", nargs=2, help="مقارنة تقريرين")
    
    args = parser.parse_args()
    
    if args.compare:
        # مقارنة تقريرين
        compare_test_results(args.compare[0], args.compare[1])
    else:
        # تشغيل اختبار الاتساق
        test_consistency(args.video, args.output, args.name)

if __name__ == "__main__":
    main()
