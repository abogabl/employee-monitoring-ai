"""
تحليل فيديو واحد بالتفصيل - Single Video Analyzer
أداة لتحليل مشكلة العد الخاطئ في فيديو محدد

الميزات:
- تحليل مفصل لكل إطار
- عرض الكشوفات بصرياً
- اختبار إعدادات مختلفة
- تشخيص المشاكل
"""

import cv2
import numpy as np
import json
import logging
from pathlib import Path
import argparse
import time

# إعداد السجلات
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

class SingleVideoAnalyzer:
    """محلل فيديو واحد بالتفصيل"""
    
    def __init__(self, video_path: str):
        self.video_path = Path(video_path)
        if not self.video_path.exists():
            raise FileNotFoundError(f"الفيديو غير موجود: {video_path}")
        
        self.results_dir = Path("video_analysis_results")
        self.results_dir.mkdir(exist_ok=True)
        
        # إعدادات مختلفة للاختبار
        self.test_configs = [
            {"name": "default", "confidence": 0.35, "iou": 0.7},
            {"name": "strict", "confidence": 0.6, "iou": 0.5},
            {"name": "loose", "confidence": 0.25, "iou": 0.8},
            {"name": "balanced", "confidence": 0.45, "iou": 0.6}
        ]
    
    def get_video_info(self):
        """الحصول على معلومات الفيديو"""
        cap = cv2.VideoCapture(str(self.video_path))
        
        info = {
            "path": str(self.video_path),
            "size_mb": self.video_path.stat().st_size / (1024 * 1024),
            "total_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            "fps": cap.get(cv2.CAP_PROP_FPS),
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "duration_sec": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / cap.get(cv2.CAP_PROP_FPS)
        }
        
        cap.release()
        return info
    
    def analyze_with_config(self, config: dict, save_frames: bool = False):
        """تحليل الفيديو مع إعدادات معينة"""
        logger.info(f"🔍 تحليل مع إعدادات {config['name']}")
        logger.info(f"   Confidence: {config['confidence']}, IoU: {config['iou']}")
        
        try:
            # تطبيق ضمان الاتساق
            from ensure_consistency import ensure_consistency
            ensure_consistency()
            
            # إنشاء المعالج
            from src.level2_video_processor import Level2VideoProcessor
            
            processor = Level2VideoProcessor(
                device="cpu",
                imgsz=416,
                conf_threshold=config["confidence"],
                enable_face_recognition=False,
                enable_activity_recognition=False,
                enable_advanced_ai=False,
                random_seed=42
            )
            
            # مجلد حفظ الإطارات
            frames_dir = None
            if save_frames:
                frames_dir = self.results_dir / f"frames_{config['name']}"
                frames_dir.mkdir(exist_ok=True)
            
            # معالجة الفيديو
            start_time = time.time()
            results = processor.process_video(
                input_path=str(self.video_path),
                output_path=str(frames_dir / "output.mp4") if frames_dir else None
            )
            processing_time = time.time() - start_time
            
            # تحليل النتائج
            analysis = {
                "config": config,
                "processing_time": processing_time,
                "detected_persons": len(results.get('statistics', [])),
                "total_detections": sum(len(stat.get('detections', [])) for stat in results.get('statistics', [])),
                "video_info": results.get('video_info', {}),
                "frame_analysis": self.analyze_frame_detections(results),
                "person_details": results.get('statistics', []),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # حفظ النتائج
            results_file = self.results_dir / f"analysis_{config['name']}.json"
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ تم الانتهاء: {analysis['detected_persons']} أشخاص في {processing_time:.2f} ثانية")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ خطأ في التحليل: {e}")
            return {"error": str(e), "config": config}
    
    def analyze_frame_detections(self, results):
        """تحليل الكشوفات في كل إطار"""
        frame_stats = {
            "frames_with_detections": 0,
            "avg_detections_per_frame": 0,
            "max_detections_in_frame": 0,
            "detection_confidence_avg": 0,
            "detection_confidence_min": 1.0,
            "detection_confidence_max": 0.0
        }
        
        total_detections = 0
        total_confidence = 0
        confidence_values = []
        
        for person_stat in results.get('statistics', []):
            detections = person_stat.get('detections', [])
            if detections:
                frame_stats["frames_with_detections"] += 1
                frame_detections = len(detections)
                total_detections += frame_detections
                
                if frame_detections > frame_stats["max_detections_in_frame"]:
                    frame_stats["max_detections_in_frame"] = frame_detections
                
                # تحليل الثقة
                for detection in detections:
                    conf = detection.get('confidence', 0)
                    confidence_values.append(conf)
                    total_confidence += conf
        
        if confidence_values:
            frame_stats["detection_confidence_avg"] = np.mean(confidence_values)
            frame_stats["detection_confidence_min"] = min(confidence_values)
            frame_stats["detection_confidence_max"] = max(confidence_values)
        
        if frame_stats["frames_with_detections"] > 0:
            frame_stats["avg_detections_per_frame"] = total_detections / frame_stats["frames_with_detections"]
        
        return frame_stats
    
    def compare_configs(self):
        """مقارنة الإعدادات المختلفة"""
        logger.info("🔄 بدء مقارنة الإعدادات المختلفة...")
        
        all_analyses = []
        
        for config in self.test_configs:
            analysis = self.analyze_with_config(config)
            all_analyses.append(analysis)
        
        # إنشاء تقرير المقارنة
        comparison = {
            "video_path": str(self.video_path),
            "video_info": self.get_video_info(),
            "analyses": all_analyses,
            "comparison_summary": self.create_comparison_summary(all_analyses),
            "recommendations": self.generate_recommendations(all_analyses),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # حفظ التقرير
        report_file = self.results_dir / "comparison_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(comparison, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📄 تقرير المقارنة: {report_file}")
        
        return comparison
    
    def create_comparison_summary(self, analyses):
        """إنشاء ملخص المقارنة"""
        summary = {
            "config_results": {},
            "best_config": None,
            "most_consistent": None,
            "fastest": None
        }
        
        fastest_time = float('inf')
        
        for analysis in analyses:
            if 'error' in analysis:
                continue
                
            config_name = analysis['config']['name']
            summary["config_results"][config_name] = {
                "detected_persons": analysis['detected_persons'],
                "processing_time": analysis['processing_time'],
                "avg_confidence": analysis['frame_analysis']['detection_confidence_avg'],
                "max_detections_frame": analysis['frame_analysis']['max_detections_in_frame']
            }
            
            # أسرع معالجة
            if analysis['processing_time'] < fastest_time:
                fastest_time = analysis['processing_time']
                summary["fastest"] = config_name
        
        return summary
    
    def generate_recommendations(self, analyses):
        """توليد توصيات بناء على التحليل"""
        recommendations = []
        
        # تحليل النتائج
        person_counts = []
        for analysis in analyses:
            if 'error' not in analysis:
                person_counts.append({
                    'config': analysis['config']['name'],
                    'count': analysis['detected_persons'],
                    'confidence': analysis['config']['confidence']
                })
        
        if not person_counts:
            return ["❌ لم يتم الحصول على نتائج صحيحة"]
        
        # ترتيب حسب عدد الأشخاص
        person_counts.sort(key=lambda x: x['count'])
        
        recommendations.extend([
            "📊 تحليل النتائج:",
            f"   • أقل عدد: {person_counts[0]['count']} أشخاص (إعداد: {person_counts[0]['config']})",
            f"   • أكثر عدد: {person_counts[-1]['count']} أشخاص (إعداد: {person_counts[-1]['config']})",
            "",
            "🎯 التوصيات:"
        ])
        
        # توصيات حسب النتائج
        if person_counts[-1]['count'] > person_counts[0]['count'] * 2:
            recommendations.extend([
                "⚠️ يوجد اختلاف كبير في النتائج بين الإعدادات",
                "• جرب زيادة confidence threshold إلى 0.5 أو أعلى",
                "• قلل IoU threshold إلى 0.5 أو أقل",
                "• تحقق من جودة الفيديو والإضاءة"
            ])
        
        if any(pc['count'] == 0 for pc in person_counts):
            recommendations.extend([
                "🔍 بعض الإعدادات لم تكتشف أي أشخاص:",
                "• قلل confidence threshold",
                "• تحقق من حجم الأشخاص في الفيديو",
                "• جرب نموذج YOLO أكبر (m أو l بدلاً من s)"
            ])
        
        return recommendations
    
    def print_summary(self, comparison):
        """طباعة ملخص النتائج"""
        print("\n" + "="*60)
        print("📊 ملخص تحليل الفيديو")
        print("="*60)
        
        video_info = comparison['video_info']
        print(f"📹 الفيديو: {video_info['path']}")
        print(f"⏱️ المدة: {video_info['duration_sec']:.1f} ثانية")
        print(f"🖼️ الأبعاد: {video_info['width']}x{video_info['height']}")
        print(f"🎬 الإطارات: {video_info['total_frames']} إطار")
        
        print("\n📈 نتائج الإعدادات المختلفة:")
        print("-" * 40)
        
        for config_name, results in comparison['comparison_summary']['config_results'].items():
            print(f"{config_name:12} | {results['detected_persons']:2d} أشخاص | {results['processing_time']:5.2f}s")
        
        print("\n💡 التوصيات:")
        for rec in comparison['recommendations']:
            print(f"   {rec}")

def main():
    parser = argparse.ArgumentParser(description='تحليل فيديو واحد بالتفصيل')
    parser.add_argument('video_path', help='مسار الفيديو')
    parser.add_argument('--save-frames', action='store_true', help='حفظ الإطارات المعالجة')
    parser.add_argument('--config', help='اختبار إعداد واحد فقط (default, strict, loose, balanced)')
    
    args = parser.parse_args()
    
    try:
        analyzer = SingleVideoAnalyzer(args.video_path)
        
        if args.config:
            # اختبار إعداد واحد
            config = next((c for c in analyzer.test_configs if c['name'] == args.config), None)
            if not config:
                print(f"❌ إعداد غير صحيح: {args.config}")
                print(f"الإعدادات المتاحة: {[c['name'] for c in analyzer.test_configs]}")
                return
            
            analysis = analyzer.analyze_with_config(config, args.save_frames)
            print(f"\n✅ تم تحليل الفيديو بإعداد {config['name']}")
            print(f"🎯 النتيجة: {analysis['detected_persons']} أشخاص")
            
        else:
            # مقارنة جميع الإعدادات
            comparison = analyzer.compare_configs()
            analyzer.print_summary(comparison)
            
    except Exception as e:
        logger.error(f"❌ خطأ: {e}")

if __name__ == "__main__":
    # إذا تم تشغيله بدون معاملات، استخدم الفيديو التجريبي
    import sys
    if len(sys.argv) == 1:
        print("Analyzing test video...")
        analyzer = SingleVideoAnalyzer("web_app/static/uploads/test_videos/test_sample.mp4")
        comparison = analyzer.compare_configs()
        analyzer.print_summary(comparison)
    else:
        main()
