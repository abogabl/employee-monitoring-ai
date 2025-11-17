"""
إصلاح جذري لمشكلة عدد الأشخاص - Radical Fix for Person Count Issue
تشخيص وإصلاح المشكلة الجذرية في عد الأشخاص
"""

import json
import logging
from pathlib import Path

# إعداد السجلات
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def analyze_current_issue():
    """تحليل المشكلة الحالية"""
    print("="*60)
    print("RADICAL DIAGNOSIS - Person Count Issue")
    print("="*60)
    
    print("\nPROBLEM:")
    print("  8 real persons → 24 detected persons")
    print("  Issue persists even with original settings")
    print("  This suggests the problem is deeper than just thresholds")
    
    print("\nPOSSIBLE ROOT CAUSES:")
    print("  1. Tracking algorithm creating multiple IDs for same person")
    print("  2. Frame processing creating duplicate detections")
    print("  3. Person merging/splitting logic issues")
    print("  4. ByteTrack tracker configuration problems")
    
    return True

def create_conservative_config():
    """إنشاء إعدادات محافظة جداً"""
    conservative_config = {
        "system": {
            "random_seed": 42,
            "deterministic_mode": True,
            "testing_mode": True,
            "consistency_version": "1.0"
        },
        "yolo": {
            "model": "yolov8s.pt",
            "imgsz": 416,
            "confidence": 0.6,  # عالي جداً لتقليل الكشوفات
            "iou": 0.4,         # منخفض لتجنب دمج الكشوفات المتقاربة
            "device": "cpu",
            "max_det": 50,      # تقليل العدد الأقصى
            "agnostic_nms": False,
            "classes": [0],
            "verbose": False
        },
        "level2_processor": {
            "frame_skip": 5,    # تخطي إطارات أكثر
            "activity_window": 15,
            "enable_advanced_ai": True,
            "enable_face_recognition": True,
            "enable_activity_recognition": True,
            "conf_threshold": 0.6,
            "yolo_model": "s",
            "random_seed": 42
        },
        "tracking": {
            "type": "bytetrack",
            "track_high_thresh": 0.8,   # عالي جداً
            "track_low_thresh": 0.3,    # عالي نسبياً
            "new_track_thresh": 0.9,    # عالي جداً لتجنب التتبع الجديد
            "max_age": 10,              # قصير لحذف التتبع السريع
            "match_thresh": 0.95        # عالي جداً للدقة
        },
        "ai_thresholds": {
            "anomaly_threshold": 0.7,
            "risk_threshold": 0.6,
            "prediction_confidence": 0.5,
            "face_similarity": 0.6
        },
        "performance": {
            "max_duration": 300,
            "enable_progress_tracking": True,
            "log_level": "INFO",
            "save_snapshots": True,
            "snapshot_quality": 95
        },
        "consistency_settings": {
            "sort_detections": True,
            "sort_by": ["confidence", "x1", "y1"],
            "round_precision": 6,
            "fixed_timestamps": False,
            "deterministic_processing": True
        }
    }
    
    return conservative_config

def create_minimal_config():
    """إنشاء إعدادات مينيمال للاختبار"""
    minimal_config = {
        "system": {
            "random_seed": 42,
            "deterministic_mode": True,
            "testing_mode": True,
            "consistency_version": "1.0"
        },
        "yolo": {
            "model": "yolov8s.pt",
            "imgsz": 320,       # حجم أصغر
            "confidence": 0.7,  # عالي جداً
            "iou": 0.3,         # منخفض جداً
            "device": "cpu",
            "max_det": 20,      # قليل جداً
            "agnostic_nms": False,
            "classes": [0],
            "verbose": False
        },
        "level2_processor": {
            "frame_skip": 10,   # تخطي إطارات كثيرة
            "activity_window": 15,
            "enable_advanced_ai": False,  # تعطيل للبساطة
            "enable_face_recognition": False,  # تعطيل للبساطة
            "enable_activity_recognition": False,  # تعطيل للبساطة
            "conf_threshold": 0.7,
            "yolo_model": "s",
            "random_seed": 42
        },
        "tracking": {
            "type": "bytetrack",
            "track_high_thresh": 0.9,   # أعلى ما يمكن
            "track_low_thresh": 0.5,    
            "new_track_thresh": 0.95,   # أعلى ما يمكن
            "max_age": 5,               # قصير جداً
            "match_thresh": 0.98        # أعلى ما يمكن
        },
        "ai_thresholds": {
            "anomaly_threshold": 0.7,
            "risk_threshold": 0.6,
            "prediction_confidence": 0.5,
            "face_similarity": 0.6
        },
        "performance": {
            "max_duration": 300,
            "enable_progress_tracking": True,
            "log_level": "INFO",
            "save_snapshots": True,
            "snapshot_quality": 95
        },
        "consistency_settings": {
            "sort_detections": True,
            "sort_by": ["confidence", "x1", "y1"],
            "round_precision": 6,
            "fixed_timestamps": False,
            "deterministic_processing": True
        }
    }
    
    return minimal_config

def apply_config(config, config_name):
    """تطبيق إعدادات معينة"""
    config_file = Path("config/unified_config.json")
    backup_file = Path(f"config/unified_config_backup_{config_name}.json")
    
    try:
        # نسخ احتياطي
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                current_config = json.load(f)
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(current_config, f, indent=2, ensure_ascii=False)
        
        # تطبيق الإعدادات الجديدة
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"Applied {config_name} config successfully")
        print(f"Backup saved to: {backup_file}")
        return True
        
    except Exception as e:
        print(f"Error applying config: {e}")
        return False

def test_with_config(config_name, config):
    """اختبار مع إعدادات معينة"""
    print(f"\n{'='*50}")
    print(f"TESTING WITH {config_name.upper()} CONFIG")
    print(f"{'='*50}")
    
    # عرض الإعدادات الرئيسية
    print("Key settings:")
    print(f"  Confidence: {config['yolo']['confidence']}")
    print(f"  IoU: {config['yolo']['iou']}")
    print(f"  Max detections: {config['yolo']['max_det']}")
    print(f"  Frame skip: {config['level2_processor']['frame_skip']}")
    print(f"  Track high thresh: {config['tracking']['track_high_thresh']}")
    print(f"  New track thresh: {config['tracking']['new_track_thresh']}")
    print(f"  Max age: {config['tracking']['max_age']}")
    
    # تطبيق الإعدادات
    if apply_config(config, config_name):
        print(f"\n{config_name} config applied successfully!")
        print("Please test your video now and report the results.")
        print("Expected: Significant reduction in person count")
        return True
    else:
        print(f"Failed to apply {config_name} config")
        return False

def main():
    """الدالة الرئيسية"""
    analyze_current_issue()
    
    print(f"\n{'='*60}")
    print("RADICAL SOLUTION APPROACH")
    print(f"{'='*60}")
    
    print("\nWe will try two approaches:")
    print("1. CONSERVATIVE: High thresholds, strict tracking")
    print("2. MINIMAL: Extreme settings, minimal features")
    
    choice = input("\nWhich approach to try first? (1=conservative, 2=minimal, 3=both): ").strip()
    
    if choice == "1" or choice == "3":
        print("\n" + "="*60)
        print("APPLYING CONSERVATIVE CONFIG")
        print("="*60)
        conservative_config = create_conservative_config()
        test_with_config("conservative", conservative_config)
        
        if choice == "1":
            return
    
    if choice == "2" or choice == "3":
        if choice == "3":
            input("\nPress Enter after testing conservative config to try minimal...")
        
        print("\n" + "="*60)
        print("APPLYING MINIMAL CONFIG")
        print("="*60)
        minimal_config = create_minimal_config()
        test_with_config("minimal", minimal_config)
    
    print(f"\n{'='*60}")
    print("NEXT STEPS")
    print(f"{'='*60}")
    print("1. Test your problematic video with the new settings")
    print("2. Report the person count results")
    print("3. If still wrong, we may need to modify the tracking algorithm itself")
    print("4. Consider using a different tracking method or custom logic")

if __name__ == "__main__":
    main()
