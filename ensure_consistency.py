"""
ضمان الاتساق في النتائج بين جميع أعضاء الفريق
Ensure Consistency Across Team Members
"""
import os
import sys
import json
import random
import numpy as np
import torch
import cv2
from pathlib import Path
from collections import defaultdict
import logging

# إعداد السجلات
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("consistency")

def ensure_consistency(seed=42, config_file="config/unified_config.json"):
    """
    ضمان الاتساق الكامل في النظام
    """
    logger.info("🔧 بدء ضمان الاتساق في النظام...")
    
    # 1. تثبيت البذور العشوائية
    set_random_seeds(seed)
    
    # 2. تحديد الإعدادات الموحدة
    config = load_unified_config(config_file)
    
    # 3. تنظيف حالة النظام
    reset_system_state()
    
    # 4. تحديد متغيرات البيئة
    set_environment_variables()
    
    # 5. التحقق من الإعدادات
    verify_system_settings()
    
    logger.info("✅ تم ضمان الاتساق بنجاح!")
    return config

def set_random_seeds(seed=42):
    """تثبيت جميع البذور العشوائية لضمان نتائج متسقة"""
    logger.info(f"🎲 تثبيت البذور العشوائية على: {seed}")
    
    # Python random
    random.seed(seed)
    
    # NumPy random
    np.random.seed(seed)
    
    # PyTorch random
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    
    # للحصول على نتائج متسقة تماماً في PyTorch
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    
    # متغير البيئة للـ hash
    os.environ['PYTHONHASHSEED'] = str(seed)
    
    # OpenCV random (إذا كان متاحاً)
    try:
        cv2.setRNGSeed(seed)
    except:
        pass
    
    logger.info("✅ تم تثبيت جميع البذور العشوائية")

def load_unified_config(config_file="config/unified_config.json"):
    """تحميل أو إنشاء الإعدادات الموحدة"""
    config_path = Path(config_file)
    
    # إنشاء مجلد config إذا لم يكن موجوداً
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not config_path.exists():
        logger.info("📝 إنشاء ملف الإعدادات الموحدة...")
        
        # إعدادات افتراضية موحدة
        unified_config = {
            "system": {
                "random_seed": 42,
                "deterministic_mode": True,
                "testing_mode": True,
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            },
            "yolo": {
                "model": "yolov8s.pt",
                "imgsz": 416,
                "confidence": 0.35,
                "iou": 0.7,
                "device": "cpu",
                "max_det": 300,
                "agnostic_nms": False,
                "classes": [0],
                "verbose": False
            },
            "level2_processor": {
                "frame_skip": 3,
                "activity_window": 15,
                "enable_advanced_ai": True,
                "enable_face_recognition": True,
                "enable_activity_recognition": True,
                "conf_threshold": 0.35,
                "yolo_model": "s"
            },
            "tracking": {
                "type": "bytetrack",
                "track_high_thresh": 0.6,
                "track_low_thresh": 0.1,
                "new_track_thresh": 0.7,
                "max_age": 30,
                "match_thresh": 0.8
            },
            "ai_thresholds": {
                "anomaly_threshold": 0.7,
                "risk_threshold": 0.6,
                "prediction_confidence": 0.5,
                "face_similarity": 0.6
            }
        }
        
        # حفظ الإعدادات
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(unified_config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ تم إنشاء ملف الإعدادات: {config_path}")
    
    # تحميل الإعدادات
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    logger.info(f"📖 تم تحميل الإعدادات الموحدة من: {config_path}")
    return config

def reset_system_state():
    """إعادة تعيين حالة النظام وتنظيف الذاكرة"""
    logger.info("🧹 تنظيف حالة النظام...")
    
    # تنظيف متغيرات النظام العامة (إذا كانت موجودة)
    global_vars_to_reset = [
        'person_data', 'track_history', 'activity_buffer', 
        'detection_cache', 'frame_cache'
    ]
    
    for var_name in global_vars_to_reset:
        if var_name in globals():
            if isinstance(globals()[var_name], dict):
                globals()[var_name] = {}
            elif isinstance(globals()[var_name], list):
                globals()[var_name] = []
            elif hasattr(globals()[var_name], 'clear'):
                globals()[var_name].clear()
    
    # تنظيف ذاكرة GPU إذا كانت متاحة
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        logger.info("🔥 تم تنظيف ذاكرة GPU")
    
    logger.info("✅ تم إعادة تعيين حالة النظام")

def set_environment_variables():
    """تحديد متغيرات البيئة للاتساق"""
    logger.info("🌍 تحديد متغيرات البيئة...")
    
    # متغيرات البيئة للاتساق
    env_vars = {
        'PYTHONHASHSEED': '42',
        'CUBLAS_WORKSPACE_CONFIG': ':4096:8',  # للـ deterministic CUDA
        'PYTORCH_CUDA_ALLOC_CONF': 'max_split_size_mb:128'
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
        logger.info(f"  {key} = {value}")
    
    logger.info("✅ تم تحديد متغيرات البيئة")

def verify_system_settings():
    """التحقق من إعدادات النظام وطباعة المعلومات"""
    logger.info("🔍 التحقق من إعدادات النظام:")
    
    # معلومات النظام
    system_info = {
        "Python": sys.version.split()[0],
        "Platform": sys.platform,
        "NumPy": np.__version__,
        "OpenCV": cv2.__version__,
        "PyTorch": torch.__version__,
        "CUDA Available": torch.cuda.is_available(),
        "CUDA Version": torch.version.cuda if torch.cuda.is_available() else "N/A",
        "Random Seed": np.random.get_state()[1][0] if len(np.random.get_state()[1]) > 0 else "Unknown"
    }
    
    for key, value in system_info.items():
        logger.info(f"  {key}: {value}")
    
    # التحقق من الاتساق
    consistency_checks = []
    
    # فحص البذرة العشوائية
    test_random = np.random.random()
    np.random.seed(42)  # إعادة تعيين للاختبار
    expected_random = np.random.random()
    np.random.seed(42)  # إعادة تعيين مرة أخرى
    
    if abs(test_random - expected_random) < 1e-10:
        consistency_checks.append("✅ البذرة العشوائية ثابتة")
    else:
        consistency_checks.append("❌ البذرة العشوائية غير ثابتة")
    
    # فحص PyTorch
    if torch.backends.cudnn.deterministic:
        consistency_checks.append("✅ PyTorch في الوضع الحتمي")
    else:
        consistency_checks.append("❌ PyTorch ليس في الوضع الحتمي")
    
    # طباعة نتائج الفحص
    logger.info("📋 نتائج فحص الاتساق:")
    for check in consistency_checks:
        logger.info(f"  {check}")
    
    return system_info

def get_system_fingerprint():
    """الحصول على بصمة النظام للمقارنة"""
    fingerprint = {
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
        "numpy_version": np.__version__,
        "opencv_version": cv2.__version__,
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "random_state_sample": str(np.random.get_state()[1][:5].tolist()),
        "deterministic_mode": torch.backends.cudnn.deterministic,
        "environment_vars": {
            key: os.environ.get(key, "Not Set") 
            for key in ['PYTHONHASHSEED', 'CUBLAS_WORKSPACE_CONFIG']
        }
    }
    
    return fingerprint

def compare_fingerprints(fp1, fp2):
    """مقارنة بصمات النظام بين عضوين في الفريق"""
    differences = []
    
    for key in fp1:
        if key not in fp2:
            differences.append(f"المفتاح {key} موجود في النظام الأول فقط")
        elif fp1[key] != fp2[key]:
            differences.append(f"{key}: {fp1[key]} != {fp2[key]}")
    
    for key in fp2:
        if key not in fp1:
            differences.append(f"المفتاح {key} موجود في النظام الثاني فقط")
    
    return differences

def create_consistency_report():
    """إنشاء تقرير الاتساق"""
    logger.info("📊 إنشاء تقرير الاتساق...")
    
    # ضمان الاتساق أولاً
    config = ensure_consistency()
    
    # الحصول على بصمة النظام
    fingerprint = get_system_fingerprint()
    
    # إنشاء التقرير
    report = {
        "timestamp": str(np.datetime64('now')),
        "config": config,
        "system_fingerprint": fingerprint,
        "consistency_status": "✅ النظام جاهز للاختبار المتسق"
    }
    
    # حفظ التقرير
    report_path = Path("consistency_report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ تم حفظ تقرير الاتساق: {report_path}")
    return report

if __name__ == "__main__":
    """تشغيل مباشر لضمان الاتساق"""
    print("Ensuring Consistency in Employee Monitoring System")
    print("=" * 50)
    
    try:
        # ضمان الاتساق
        config = ensure_consistency()
        
        # إنشاء تقرير
        report = create_consistency_report()
        
        print("\nConsistency ensured successfully!")
        print("Next steps:")
        print("  1. Share unified_config.json with team")
        print("  2. Ensure all members use same settings")
        print("  3. Test results using test_consistency.py")
        print("  4. Compare results between team members")
        
    except Exception as e:
        logger.error(f"Error ensuring consistency: {e}")
        sys.exit(1)
