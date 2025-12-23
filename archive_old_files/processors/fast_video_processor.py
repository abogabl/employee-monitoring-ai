"""
معالج فيديو سريع جداً للاختبار
محسن للسرعة مع الحفاظ على التحسينات الأساسية
"""
from __future__ import annotations
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import cv2
import numpy as np

from .detection_tracking import PersonDetector, PersonTracker
from .activity_recognition import ActivityRecognizer
from .activity_rules import ActivityRules
from .utils import draw_text_with_background

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fast_video_processor")


class FastVideoProcessor:
    """معالج فيديو سريع جداً مع التحسينات الأساسية"""
    
    def __init__(
        self,
        device: str = "cpu",
        imgsz: int = 320,
        conf_threshold: float = 0.35,
        enable_activity_recognition: bool = True,
        yolo_model: str = "n",  # nano للسرعة القصوى
        activity_window: int = 10  # نافذة أصغر للسرعة
    ):
        self.device = device
        self.imgsz = imgsz
        self.conf_threshold = conf_threshold
        self.enable_activity = enable_activity_recognition
        
        logger.info("تهيئة المعالج السريع...")
        
        # كاشف الأشخاص - محسن للسرعة
        try:
            self.person_detector = PersonDetector(
                model_size=yolo_model,
                device=device,
                imgsz=int(imgsz),
                conf=0.4,  # عتبة أعلى للسرعة
                iou=0.6    # IOU أعلى لتقليل الكشوفات
            )
            logger.info(f"✓ كاشف الأشخاص السريع: yolov8{yolo_model}, imgsz={imgsz}")
        except Exception as e:
            logger.error(f"فشل تهيئة كاشف الأشخاص: {e}")
            self.person_detector = None
        
        # تتبع مبسط
        self.tracker = PersonTracker(max_disappeared=30, max_distance=200.0)
        
        # كشف الأنشطة مبسط
        if enable_activity_recognition:
            try:
                activity_rules = ActivityRules(config_path="config/activity_config.json")
                self.activity_detector = ActivityRecognizer(
                    use_pose=True,
                    use_objects=False,  # تعطيل كشف الأشياء للسرعة
                    use_motion=True,
                    smoothing_seconds=3.0,  # تنعيم أقل
                    fps_hint=15.0,
                    rules=activity_rules,
                    window_size=activity_window,
                    use_ema=False,
                    ema_alpha=0.3
                )
                logger.info(f"✓ كاشف الأنشطة السريع: window={activity_window}")
            except Exception as e:
                logger.warning(f"فشل تهيئة كاشف الأنشطة: {e}")
                self.activity_detector = None
        else:
            self.activity_detector = None
        
        logger.info("✅ المعالج السريع جاهز")
    
    def process_video(
        self,
        input_path: str,
        output_path: str,
        frame_skip: int = 5,  # تخطي أكثر للسرعة
        max_duration: int = 30,  # حد أقصى للاختبار
        task_id: Optional[str] = None,
        enable_progress_tracking: bool = True
    ) -> Dict[str, Any]:
        """معالجة سريعة للفيديو"""
        start_time = time.time()
        logger.info(f"🚀 بدء المعالجة السريعة: {input_path}")
        
        # فتح الفيديو
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            return {"success": False, "error": "فشل فتح الفيديو"}
        
        # معلومات الفيديو
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # تقليل حجم الإخراج للسرعة
        output_width = min(width, 640)
        output_height = int(height * (output_width / width))
        
        logger.info(f"📊 فيديو: {total_frames} إطار، {fps:.1f} FPS، إخراج: {output_width}x{output_height}")
        
        # إعداد كاتب الفيديو
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (output_width, output_height))
        
        # متغيرات التتبع
        person_data = {}
        frame_num = 0
        processed_frames = 0
        
        # معالجة سريعة
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_num += 1
            current_time = frame_num / fps
            
            # حد أقصى للمدة
            if max_duration > 0 and current_time > max_duration:
                logger.info(f"⏰ وصل للحد الأقصى: {max_duration}s")
                break
            
            # تخطي الإطارات للسرعة
            if frame_num % frame_skip != 0:
                continue
            
            processed_frames += 1
            
            # تصغير الإطار للسرعة
            if frame.shape[1] > 640:
                scale = 640 / frame.shape[1]
                new_width = int(frame.shape[1] * scale)
                new_height = int(frame.shape[0] * scale)
                frame = cv2.resize(frame, (new_width, new_height))
            
            # كشف سريع للأشخاص
            if self.person_detector:
                detections = self.person_detector.detect(frame)
                
                # تتبع مبسط
                tracked_objects = self.tracker.update(detections)
                
                # معالجة سريعة لكل شخص
                for track_id, track_data in tracked_objects.items():
                    x1, y1, x2, y2 = track_data['box']
                    conf = 0.8  # ثقة افتراضية للمسارات المتتبعة
                    
                    # تهيئة بيانات الشخص
                    if track_id not in person_data:
                        person_data[track_id] = {
                            'name': 'Unknown',
                            'activities': [],
                            'snapshot': None,
                            'first_seen': current_time,
                            'last_seen': current_time,
                            'total_confidence': 0.0,
                            'detection_count': 0
                        }
                    
                    # تحديث بيانات الشخص
                    person_data[track_id]['last_seen'] = current_time
                    person_data[track_id]['total_confidence'] += conf
                    person_data[track_id]['detection_count'] += 1
                    
                    # كشف النشاط السريع
                    activity = 'working'  # افتراضي محسن
                    confidence = 0.8
                    
                    if self.activity_detector:
                        try:
                            result = self.activity_detector.process_person(
                                frame=frame,
                                person_box=(x1, y1, x2, y2),
                                track_history={},
                                yolo_detections=[],  # بدون أشياء للسرعة
                                track_id=track_id,
                                curr_time=current_time
                            )
                            activity = result.activity
                            confidence = result.confidence
                        except Exception as e:
                            if processed_frames % 50 == 0:
                                logger.debug(f"خطأ في كشف النشاط: {e}")
                    
                    # حفظ النشاط
                    person_data[track_id]['activities'].append((current_time, activity))
                    
                    # حفظ snapshot مرة واحدة فقط
                    if person_data[track_id]['snapshot'] is None:
                        try:
                            person_crop = frame[y1:y2, x1:x2]
                            if person_crop.size > 0:
                                snapshot_dir = Path("web_app/static/uploads/test_videos/snapshots")
                                snapshot_dir.mkdir(parents=True, exist_ok=True)
                                snapshot_name = f"person_{track_id}_{int(start_time)}.jpg"
                                snapshot_path = snapshot_dir / snapshot_name
                                cv2.imwrite(str(snapshot_path), person_crop)
                                person_data[track_id]['snapshot'] = f"uploads/test_videos/snapshots/{snapshot_name}"
                        except Exception:
                            pass
                    
                    # رسم مبسط
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    text = f"ID:{track_id} | {activity}"
                    cv2.putText(frame, text, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # تصغير الإطار للإخراج
            if frame.shape[1] != output_width:
                frame = cv2.resize(frame, (output_width, output_height))
            
            # كتابة الإطار
            out.write(frame)
            
            # تقرير التقدم كل 25 إطار
            if processed_frames % 25 == 0:
                progress = min(95, (current_time / max_duration) * 100) if max_duration > 0 else (frame_num / total_frames) * 100
                logger.info(f"⚡ سريع: {progress:.0f}% ({processed_frames} إطار)")
        
        # إنهاء المعالجة
        cap.release()
        out.release()
        
        processing_time = time.time() - start_time
        logger.info(f"✅ انتهت المعالجة السريعة في {processing_time:.1f} ثانية")
        
        # حساب الإحصائيات
        statistics = []
        for track_id, data in person_data.items():
            if not data['activities']:
                continue
            
            # حساب مدة كل نشاط
            activity_durations = {}
            for i, (timestamp, activity) in enumerate(data['activities']):
                if activity not in activity_durations:
                    activity_durations[activity] = 0.0
                
                if i < len(data['activities']) - 1:
                    next_timestamp = data['activities'][i + 1][0]
                    duration = next_timestamp - timestamp
                else:
                    duration = data['last_seen'] - timestamp
                
                activity_durations[activity] += duration
            
            # النشاط الأكثر شيوعاً
            top_activity = max(activity_durations.keys(), key=lambda k: activity_durations[k]) if activity_durations else 'unknown'
            
            # متوسط الثقة
            avg_confidence = data['total_confidence'] / max(data['detection_count'], 1)
            
            # إحصائيات الشخص
            person_stats = {
                'track_id': track_id,
                'name': data['name'],
                'duration': data['last_seen'] - data['first_seen'],
                'top_activity': top_activity,
                'avg_confidence': round(avg_confidence, 2),
                'count': data['detection_count'],
                'snapshot': data['snapshot'],
                'working_duration': activity_durations.get('working', 0.0),
                'phone_duration': activity_durations.get('on_phone', 0.0),
                'sleeping_duration': activity_durations.get('sleeping', 0.0)
            }
            
            statistics.append(person_stats)
            
            logger.info(f"👤 {track_id}: {top_activity} ({person_stats['duration']:.1f}s)")
        
        return {
            "success": True,
            "processing_time": round(processing_time, 2),
            "frames_processed": processed_frames,
            "total_frames": total_frames,
            "statistics": statistics,
            "output_path": output_path
        }
