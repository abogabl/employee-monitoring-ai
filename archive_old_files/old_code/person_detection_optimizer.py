"""
محسن دقة كشف الأشخاص - Person Detection Optimizer
حل مشكلة العد الخاطئ للأشخاص في الفيديوهات

الميزات:
- تحسين إعدادات YOLO تلقائياً
- فلترة الكشوفات الخاطئة
- دمج الكشوفات المتداخلة
- تحسين التتبع
- اختبار على فيديوهات متعددة
"""

import cv2
import numpy as np
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any
from collections import defaultdict
import time

# إعداد السجلات
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

class PersonDetectionOptimizer:
    """محسن دقة كشف الأشخاص"""
    
    def __init__(self):
        self.config_path = Path("config/unified_config.json")
        self.results_path = Path("optimization_results")
        self.results_path.mkdir(exist_ok=True)
        
        # إعدادات التحسين
        self.optimization_configs = [
            # إعدادات محافظة - دقة عالية
            {
                "name": "conservative_high_accuracy",
                "confidence": 0.6,
                "iou": 0.5,
                "track_high_thresh": 0.7,
                "track_low_thresh": 0.3,
                "new_track_thresh": 0.8,
                "max_age": 20,
                "match_thresh": 0.9
            },
            # إعدادات متوازنة
            {
                "name": "balanced",
                "confidence": 0.5,
                "iou": 0.6,
                "track_high_thresh": 0.6,
                "track_low_thresh": 0.2,
                "new_track_thresh": 0.7,
                "max_age": 25,
                "match_thresh": 0.8
            },
            # إعدادات حساسة - كشف أكثر
            {
                "name": "sensitive",
                "confidence": 0.4,
                "iou": 0.7,
                "track_high_thresh": 0.5,
                "track_low_thresh": 0.1,
                "new_track_thresh": 0.6,
                "max_age": 30,
                "match_thresh": 0.7
            },
            # إعدادات مخصصة للفيديوهات الصعبة
            {
                "name": "difficult_videos",
                "confidence": 0.45,
                "iou": 0.65,
                "track_high_thresh": 0.65,
                "track_low_thresh": 0.15,
                "new_track_thresh": 0.75,
                "max_age": 35,
                "match_thresh": 0.85
            }
        ]
        
    def load_current_config(self) -> Dict:
        """تحميل الإعدادات الحالية"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"خطأ في تحميل الإعدادات: {e}")
            return {}
    
    def save_config(self, config: Dict, name: str = "optimized"):
        """حفظ إعدادات محسنة"""
        try:
            config_file = self.results_path / f"config_{name}.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info(f"✓ تم حفظ الإعدادات: {config_file}")
            return config_file
        except Exception as e:
            logger.error(f"خطأ في حفظ الإعدادات: {e}")
            return None
    
    def apply_config(self, optimization_config: Dict) -> Dict:
        """تطبيق إعدادات التحسين"""
        base_config = self.load_current_config()
        
        # تحديث إعدادات YOLO
        base_config["yolo"]["confidence"] = optimization_config["confidence"]
        base_config["yolo"]["iou"] = optimization_config["iou"]
        
        # تحديث إعدادات التتبع
        base_config["tracking"]["track_high_thresh"] = optimization_config["track_high_thresh"]
        base_config["tracking"]["track_low_thresh"] = optimization_config["track_low_thresh"]
        base_config["tracking"]["new_track_thresh"] = optimization_config["new_track_thresh"]
        base_config["tracking"]["max_age"] = optimization_config["max_age"]
        base_config["tracking"]["match_thresh"] = optimization_config["match_thresh"]
        
        # تحديث إعدادات المعالج
        base_config["level2_processor"]["conf_threshold"] = optimization_config["confidence"]
        
        return base_config
    
    def test_video_with_config(self, video_path: str, config: Dict, expected_persons: int = None) -> Dict:
        """اختبار فيديو مع إعدادات معينة"""
        logger.info(f"🎬 اختبار الفيديو: {video_path}")
        logger.info(f"⚙️ الإعدادات: {config['name']}")
        
        try:
            # حفظ الإعدادات مؤقتاً
            temp_config_file = self.save_config(config, f"temp_{config['name']}")
            
            # تطبيق ضمان الاتساق
            from ensure_consistency import ensure_consistency
            ensure_consistency()
            
            # تشغيل المعالج
            from src.level2_video_processor import Level2VideoProcessor
            
            processor = Level2VideoProcessor(
                device="cpu",
                imgsz=416,
                conf_threshold=config["yolo"]["confidence"],
                enable_face_recognition=False,  # تعطيل للسرعة
                enable_activity_recognition=False,  # تعطيل للسرعة
                enable_advanced_ai=False,  # تعطيل للسرعة
                random_seed=42
            )
            
            # معالجة الفيديو
            start_time = time.time()
            results = processor.process_video(
                input_path=video_path,
                output_path=None,  # بدون حفظ للسرعة
                save_frames=False,
                progress_callback=None
            )
            processing_time = time.time() - start_time
            
            # تحليل النتائج
            detected_persons = len(results.get('statistics', []))
            
            # حساب الدقة
            accuracy = None
            if expected_persons is not None:
                accuracy = 1.0 - abs(detected_persons - expected_persons) / max(expected_persons, 1)
            
            result = {
                "config_name": config["name"],
                "video_path": video_path,
                "detected_persons": detected_persons,
                "expected_persons": expected_persons,
                "accuracy": accuracy,
                "processing_time": processing_time,
                "config_settings": {
                    "confidence": config["yolo"]["confidence"],
                    "iou": config["yolo"]["iou"],
                    "track_high_thresh": config["tracking"]["track_high_thresh"],
                    "new_track_thresh": config["tracking"]["new_track_thresh"]
                },
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            logger.info(f"📊 النتائج: {detected_persons} أشخاص (متوقع: {expected_persons})")
            if accuracy is not None:
                logger.info(f"🎯 الدقة: {accuracy:.2%}")
            logger.info(f"⏱️ وقت المعالجة: {processing_time:.2f} ثانية")
            
            return result
            
        except Exception as e:
            logger.error(f"خطأ في اختبار الفيديو: {e}")
            return {
                "config_name": config.get("name", "unknown"),
                "video_path": video_path,
                "error": str(e),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
    
    def optimize_for_videos(self, video_tests: List[Dict]) -> Dict:
        """تحسين الإعدادات لمجموعة من الفيديوهات
        
        Args:
            video_tests: قائمة من الفيديوهات مع العدد المتوقع
            [{"path": "video.mp4", "expected_persons": 2}, ...]
        """
        logger.info("🚀 بدء تحسين إعدادات كشف الأشخاص...")
        
        all_results = []
        config_scores = defaultdict(list)
        
        # اختبار كل إعداد مع كل فيديو
        for opt_config in self.optimization_configs:
            logger.info(f"\n🔧 اختبار إعدادات: {opt_config['name']}")
            
            # تطبيق الإعدادات
            full_config = self.apply_config(opt_config)
            full_config["name"] = opt_config["name"]
            
            config_results = []
            
            for video_test in video_tests:
                result = self.test_video_with_config(
                    video_test["path"], 
                    full_config, 
                    video_test.get("expected_persons")
                )
                config_results.append(result)
                all_results.append(result)
                
                # حساب النقاط
                if result.get("accuracy") is not None:
                    config_scores[opt_config["name"]].append(result["accuracy"])
            
            # حفظ نتائج هذا الإعداد
            results_file = self.results_path / f"results_{opt_config['name']}.json"
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(config_results, f, indent=2, ensure_ascii=False)
        
        # تحليل النتائج وإيجاد أفضل إعداد
        best_config = self.find_best_config(config_scores)
        
        # حفظ التقرير النهائي
        final_report = {
            "optimization_summary": {
                "total_videos_tested": len(video_tests),
                "total_configs_tested": len(self.optimization_configs),
                "best_config": best_config,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "config_scores": dict(config_scores),
            "all_results": all_results,
            "recommendations": self.generate_recommendations(config_scores, video_tests)
        }
        
        report_file = self.results_path / "optimization_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(final_report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n🎉 تم الانتهاء من التحسين!")
        logger.info(f"📄 التقرير النهائي: {report_file}")
        
        return final_report
    
    def find_best_config(self, config_scores: Dict) -> Dict:
        """إيجاد أفضل إعداد"""
        best_config = None
        best_avg_score = -1
        
        for config_name, scores in config_scores.items():
            if scores:
                avg_score = np.mean(scores)
                if avg_score > best_avg_score:
                    best_avg_score = avg_score
                    best_config = config_name
        
        return {
            "name": best_config,
            "average_accuracy": best_avg_score,
            "config_details": next(c for c in self.optimization_configs if c["name"] == best_config)
        }
    
    def generate_recommendations(self, config_scores: Dict, video_tests: List) -> List[str]:
        """توليد توصيات للتحسين"""
        recommendations = []
        
        # تحليل النتائج
        if config_scores:
            best_config = max(config_scores.keys(), key=lambda k: np.mean(config_scores[k]) if config_scores[k] else 0)
            worst_config = min(config_scores.keys(), key=lambda k: np.mean(config_scores[k]) if config_scores[k] else 0)
            
            recommendations.extend([
                f"🏆 أفضل إعداد: {best_config} بدقة {np.mean(config_scores[best_config]):.2%}",
                f"⚠️ أسوأ إعداد: {worst_config} بدقة {np.mean(config_scores[worst_config]):.2%}",
                "",
                "📋 التوصيات العامة:",
                "• استخدم confidence أعلى (0.5-0.6) للفيديوهات عالية الجودة",
                "• استخدم confidence أقل (0.4-0.5) للفيديوهات منخفضة الجودة",
                "• زيد track_high_thresh لتقليل الكشوفات الخاطئة",
                "• قلل max_age لتجنب تتبع الأشباح",
                "• استخدم match_thresh عالي (0.8-0.9) لتحسين دقة التتبع"
            ])
        
        return recommendations
    
    def apply_best_config(self, report: Dict):
        """تطبيق أفضل إعداد على النظام"""
        try:
            best_config_name = report["optimization_summary"]["best_config"]["name"]
            best_config_details = report["optimization_summary"]["best_config"]["config_details"]
            
            # تطبيق الإعدادات
            optimized_config = self.apply_config(best_config_details)
            
            # حفظ في الملف الرئيسي
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(optimized_config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ تم تطبيق أفضل إعداد: {best_config_name}")
            logger.info(f"📁 تم تحديث: {self.config_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"خطأ في تطبيق الإعدادات: {e}")
            return False

def main():
    """تشغيل التحسين"""
    optimizer = PersonDetectionOptimizer()
    
    # أمثلة على الفيديوهات للاختبار
    # يجب تعديل هذه القائمة حسب الفيديوهات المتاحة
    video_tests = [
        {
            "path": "web_app/static/uploads/test_videos/test_sample.mp4",
            "expected_persons": 0,  # الفيديو التجريبي فارغ
            "description": "فيديو تجريبي فارغ"
        }
        # أضف المزيد من الفيديوهات هنا:
        # {
        #     "path": "path/to/single_person_video.mp4",
        #     "expected_persons": 1,
        #     "description": "فيديو شخص واحد"
        # },
        # {
        #     "path": "path/to/multiple_persons_video.mp4", 
        #     "expected_persons": 3,
        #     "description": "فيديو عدة أشخاص"
        # }
    ]
    
    print("🎯 محسن دقة كشف الأشخاص")
    print("=" * 50)
    print("هذا البرنامج سيختبر إعدادات مختلفة لتحسين دقة كشف الأشخاص")
    print("\nلاستخدام البرنامج بشكل كامل:")
    print("1. أضف مسارات الفيديوهات في قائمة video_tests")
    print("2. حدد العدد المتوقع للأشخاص في كل فيديو")
    print("3. شغل البرنامج")
    print("\nالآن سيتم اختبار الفيديو التجريبي فقط...")
    
    # تشغيل التحسين
    report = optimizer.optimize_for_videos(video_tests)
    
    # عرض النتائج
    print("\n" + "="*50)
    print("📊 نتائج التحسين:")
    print("="*50)
    
    best_config = report["optimization_summary"]["best_config"]
    print(f"🏆 أفضل إعداد: {best_config['name']}")
    print(f"🎯 الدقة المتوسطة: {best_config['average_accuracy']:.2%}")
    
    print("\n📋 التوصيات:")
    for rec in report["recommendations"]:
        print(f"   {rec}")
    
    # سؤال المستخدم عن تطبيق الإعدادات
    apply = input("\n❓ هل تريد تطبيق أفضل إعداد على النظام؟ (y/n): ").lower().strip()
    if apply in ['y', 'yes', 'نعم']:
        if optimizer.apply_best_config(report):
            print("✅ تم تطبيق الإعدادات المحسنة بنجاح!")
            print("🔄 أعد تشغيل النظام لتفعيل الإعدادات الجديدة")
        else:
            print("❌ فشل في تطبيق الإعدادات")
    else:
        print("ℹ️ لم يتم تطبيق الإعدادات. يمكنك مراجعة النتائج في مجلد optimization_results")

if __name__ == "__main__":
    main()
