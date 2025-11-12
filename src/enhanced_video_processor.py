"""
معالج فيديو محسّن مع تحسينات المستوى 1
يستخدم yolov8m، التنعيم الزمني، وفلترة جودة الوجوه
"""
from __future__ import annotations
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import cv2
import numpy as np

from .detection_tracking import PersonDetector, PersonTracker
from .face_recognition_system import FaceRecognitionSystem
from .activity_recognition import ActivityRecognizer
from .activity_rules import ActivityRules
from .utils import crop_person, draw_text_with_background

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("enhanced_video_processor")


class EnhancedVideoProcessor:
    """معالج فيديو محسّن مع تحسينات المستوى 1"""
    
    def __init__(
        self,
        device: str = "cpu",
        imgsz: int = 640,
        conf_threshold: float = 0.35,  # العتبة المحسنة
        enable_face_recognition: bool = True,
        enable_activity_recognition: bool = True,
        detection_only: bool = False,
        yolo_model: str = "m",  # النموذج المحسن
        activity_window: int = 15,  # نافذة التنعيم
        use_ema: bool = False,
        ema_alpha: float = 0.2
    ):
        self.device = device
        self.imgsz = imgsz
        self.conf_threshold = conf_threshold
        self.enable_face = enable_face_recognition
        self.enable_activity = enable_activity_recognition
        self.detection_only = bool(detection_only)
        
        # تهيئة المكونات مع التحسينات الجديدة
        logger.info("تهيئة المعالج المحسّن مع تحسينات المستوى 1...")
        
        # كاشف الأشخاص مع التحسينات
        try:
            self.person_detector = PersonDetector(
                model_size=yolo_model,  # yolov8m بدلاً من yolov8n
                device=device,
                imgsz=int(imgsz),
                conf=0.35,  # العتبة المحسنة
                iou=0.5     # IOU المحسن
            )
            logger.info(f"✓ تم تهيئة كاشف الأشخاص المحسّن: yolov8{yolo_model}, conf=0.35, iou=0.5")
        except Exception as e:
            logger.error(f"فشل تهيئة كاشف الأشخاص: {e}")
            self.person_detector = None
        
        # تتبع الأشخاص
        if not self.detection_only:
            self.tracker = PersonTracker(max_disappeared=90, max_distance=150.0)
            logger.info("✓ تم تهيئة PersonTracker")
        else:
            self.tracker = None
        
        # التعرف على الوجوه مع فلترة الجودة
        if enable_face_recognition:
            try:
                self.face_recognizer = FaceRecognitionSystem()
                logger.info("✓ تم تهيئة التعرف على الوجوه مع فلترة الجودة")
            except Exception as e:
                logger.warning(f"فشل التعرف على الوجوه: {e}")
                self.face_recognizer = None
        else:
            self.face_recognizer = None
        
        # كشف الأنشطة مع التنعيم الزمني المحسن
        if enable_activity_recognition:
            try:
                activity_rules = ActivityRules(config_path="config/activity_config.json")
                self.activity_detector = ActivityRecognizer(
                    use_pose=True,
                    use_objects=True,
                    use_motion=True,
                    smoothing_seconds=5.0,
                    fps_hint=25.0,
                    rules=activity_rules,
                    window_size=activity_window,  # التنعيم الزمني المحسن
                    use_ema=use_ema,
                    ema_alpha=ema_alpha
                )
                logger.info(f"✓ تم تهيئة ActivityRecognizer المحسّن: window={activity_window}, ema={use_ema}")
            except Exception as e:
                logger.error(f"فشل تهيئة ActivityRecognizer: {e}")
                self.activity_detector = None
        else:
            self.activity_detector = None
        
        logger.info("✅ المعالج المحسّن جاهز")
    
    def process_video(
        self,
        input_path: str,
        output_path: str,
        frame_skip: int = 2,
        max_duration: int = -1,
        task_id: Optional[str] = None,
        enable_progress_tracking: bool = True
    ) -> Dict[str, Any]:
        """معالجة الفيديو مع التحسينات الجديدة"""
        start_time = time.time()
        logger.info(f"🎬 بدء معالجة الفيديو المحسّن: {input_path}")
        
        # فتح الفيديو
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            return {"success": False, "error": "فشل فتح الفيديو"}
        
        # معلومات الفيديو
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        logger.info(f"📊 معلومات الفيديو: {total_frames} إطار، {fps:.1f} FPS، {width}x{height}")
        
        # إعداد كاتب الفيديو
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        # متغيرات التتبع
        person_data = {}
        frame_num = 0
        processed_frames = 0
        
        # معالجة الإطارات
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_num += 1
            current_time = frame_num / fps
            
            # تخطي الإطارات حسب الإعداد
            if frame_num % frame_skip != 0:
                continue
            
            processed_frames += 1
            
            # حد أقصى للمدة
            if max_duration > 0 and current_time > max_duration:
                break
            
            # كشف الأشخاص
            if self.person_detector:
                detections = self.person_detector.detect(frame)
                
                # تتبع الأشخاص
                if self.tracker:
                    tracked_objects = self.tracker.update(detections)
                else:
                    tracked_objects = [(i, det) for i, det in enumerate(detections)]
                
                # معالجة كل شخص
                for track_id, detection in tracked_objects:
                    x1, y1, x2, y2 = detection['box']
                    conf = detection['conf']
                    
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
                    
                    # التعرف على الوجه
                    if self.face_recognizer:
                        try:
                            person_crop = frame[y1:y2, x1:x2]
                            if person_crop.size > 0:
                                faces = self.face_recognizer.detect_faces(person_crop)
                                if faces:
                                    best_face = max(faces, key=lambda f: f.get('det_score', 0.0))
                                    matches = self.face_recognizer.recognize_face(best_face['embedding'])
                                    if matches:
                                        person_data[track_id]['name'] = matches[0]['name']
                        except Exception as e:
                            if processed_frames % 100 == 0:  # تقليل الرسائل
                                logger.debug(f"خطأ في التعرف على الوجه: {e}")
                    
                    # كشف النشاط مع التحسينات الجديدة
                    activity = 'unknown'
                    confidence = 0.0
                    
                    if self.activity_detector:
                        try:
                            # كشف الأشياء للسياق
                            yolo_detections = []
                            if hasattr(self.person_detector, 'model'):
                                try:
                                    results = self.person_detector.model.predict(
                                        frame, conf=0.3, classes=None, verbose=False
                                    )
                                    if results and results[0].boxes is not None:
                                        for box in results[0].boxes:
                                            cls_id = int(box.cls[0].item())
                                            conf_obj = float(box.conf[0].item())
                                            xyxy = box.xyxy[0].cpu().numpy().astype(int)
                                            yolo_detections.append({
                                                'conf': conf_obj,
                                                'box': tuple(xyxy),
                                                'class': cls_id
                                            })
                                except Exception:
                                    pass
                            
                            # استخدام ActivityRecognizer المحسن
                            result = self.activity_detector.process_person(
                                frame=frame,
                                person_box=(x1, y1, x2, y2),
                                track_history={},
                                yolo_detections=yolo_detections,
                                track_id=track_id,
                                curr_time=current_time
                            )
                            activity = result.activity
                            confidence = result.confidence
                            
                        except Exception as e:
                            if processed_frames % 100 == 0:
                                logger.debug(f"خطأ في كشف النشاط: {e}")
                    
                    # حفظ النشاط
                    person_data[track_id]['activities'].append((current_time, activity))
                    
                    # حفظ snapshot
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
                        except Exception as e:
                            logger.debug(f"خطأ في حفظ الصورة: {e}")
                    
                    # رسم النتائج على الإطار
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # النص
                    name = person_data[track_id]['name']
                    text = f"ID:{track_id} {name} | {activity} ({confidence:.2f})"
                    draw_text_with_background(frame, text, (x1, y1-10), 
                                            font_scale=0.6, thickness=1, 
                                            text_color=(255, 255, 255), bg_color=(0, 0, 0))
            
            # كتابة الإطار
            out.write(frame)
            
            # تقرير التقدم
            if processed_frames % 50 == 0:
                progress = (frame_num / total_frames) * 100
                logger.info(f"📈 التقدم: {progress:.1f}% ({processed_frames} إطار معالج)")
        
        # إنهاء المعالجة
        cap.release()
        out.release()
        
        processing_time = time.time() - start_time
        logger.info(f"✅ انتهت المعالجة في {processing_time:.1f} ثانية")
        
        # حساب الإحصائيات النهائية
        statistics = []
        for track_id, data in person_data.items():
            if not data['activities']:
                continue
            
            # حساب مدة كل نشاط
            activity_durations = {}
            for i, (timestamp, activity) in enumerate(data['activities']):
                if activity not in activity_durations:
                    activity_durations[activity] = 0.0
                
                # حساب المدة حتى النشاط التالي أو نهاية الفيديو
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
            
            logger.info(f"👤 الشخص {track_id} ({data['name']}): {top_activity} لمدة {person_stats['duration']:.1f}s")
        
        return {
            "success": True,
            "processing_time": round(processing_time, 2),
            "frames_processed": processed_frames,
            "total_frames": total_frames,
            "statistics": statistics,
            "output_path": output_path
        }
