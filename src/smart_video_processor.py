"""
معالج فيديو ذكي محسن للدقة
يركز على التصنيف الصحيح للأنشطة مع السرعة المقبولة
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
from .utils import draw_text_with_background

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smart_video_processor")


class SmartVideoProcessor:
    """معالج فيديو ذكي مع تصنيف محسن للأنشطة"""
    
    def __init__(
        self,
        device: str = "cpu",
        imgsz: int = 416,
        conf_threshold: float = 0.35,
        enable_face_recognition: bool = True,
        enable_activity_recognition: bool = True,
        yolo_model: str = "s",  # توازن بين السرعة والدقة
        activity_window: int = 15
    ):
        self.device = device
        self.imgsz = imgsz
        self.conf_threshold = conf_threshold
        self.enable_face = enable_face_recognition
        self.enable_activity = enable_activity_recognition
        
        logger.info("تهيئة المعالج الذكي...")
        
        # Phase 11: استخدام YOLO مع ByteTrack المدمج بدلاً من PersonTracker المخصص
        try:
            from ultralytics import YOLO
            self.yolo_model = YOLO(f"yolov8{yolo_model}.pt")
            self.use_bytetrack = True
            logger.info(f"✓ YOLO + ByteTrack: yolov8{yolo_model}, imgsz={imgsz}")
        except Exception as e:
            logger.error(f"فشل تهيئة YOLO: {e}")
            self.yolo_model = None
            self.use_bytetrack = False
        
        # الاحتفاظ بالكاشف القديم كـ fallback
        self.person_detector = None
        self.tracker = None
        
        # التعرف على الوجوه
        if enable_face_recognition:
            try:
                self.face_recognizer = FaceRecognitionSystem()
                logger.info("✓ تم تهيئة التعرف على الوجوه مع فلترة الجودة")
            except Exception as e:
                logger.warning(f"فشل التعرف على الوجوه: {e}")
                self.face_recognizer = None
        else:
            self.face_recognizer = None
        
        # كشف الأنشطة محسن
        if enable_activity_recognition:
            try:
                activity_rules = ActivityRules(config_path="config/activity_config.json")
                self.activity_detector = ActivityRecognizer(
                    use_pose=True,
                    use_objects=True,  # تفعيل كشف الأشياء للدقة
                    use_motion=True,
                    smoothing_seconds=4.0,
                    fps_hint=20.0,
                    rules=activity_rules,
                    window_size=activity_window,
                    use_ema=False,  # majority vote للاستقرار
                    ema_alpha=0.2
                )
                logger.info(f"✓ كاشف الأنشطة الذكي: window={activity_window}, objects=True")
            except Exception as e:
                logger.warning(f"فشل تهيئة كاشف الأنشطة: {e}")
                self.activity_detector = None
        else:
            self.activity_detector = None
        
        logger.info("✅ المعالج الذكي جاهز")
    
    def smart_classify_activity(
        self, 
        x1: int, y1: int, x2: int, y2: int, 
        frame_height: int, frame_width: int, 
        motion_level: float
    ) -> Tuple[str, float]:
        """تصنيف ذكي للأنشطة بناءً على الوضعية والحركة"""
        
        person_width = x2 - x1
        person_height = y2 - y1
        
        if person_height <= 0:
            return 'idle', 0.5
        
        # تحليل الوضعية
        center_y = (y1 + y2) / 2
        relative_position = center_y / frame_height
        aspect_ratio = person_width / max(person_height, 1)
        
        # قواعد التصنيف الذكي المحسنة
        if aspect_ratio > 1.3:  # عريض جداً = مستلقي بوضوح
            if relative_position > 0.5:
                return 'sleeping', 0.9
            else:
                return 'sleeping', 0.8
        elif aspect_ratio > 1.1 and relative_position > 0.6:
            if motion_level < 0.03:
                return 'sleeping', 0.85
            else:
                return 'idle', 0.7
        elif relative_position < 0.3:  # في الأعلى = جالس منتصب
            if motion_level > 0.08:
                return 'working', 0.85
            else:
                return 'working', 0.7
        elif relative_position > 0.75:  # في الأسفل جداً
            if motion_level < 0.05:
                return 'sleeping', 0.8
            else:
                return 'idle', 0.6
        else:  # في الوسط
            if motion_level > 0.12:
                return 'working', 0.8
            elif motion_level < 0.03:
                if aspect_ratio > 0.9 and relative_position > 0.5:
                    return 'sleeping', 0.7
                else:
                    return 'idle', 0.6
            else:
                return 'working', 0.75
    
    def _classify_activity_smart(self, person_box: Tuple[int, int, int, int], frame: np.ndarray, motion_level: float = 0.0) -> Tuple[str, float]:
        """تصنيف ذكي للنشاط بناءً على الوضعية والحركة"""
        x1, y1, x2, y2 = person_box
        
        # حساب نسبة الشخص في الإطار
        person_height = y2 - y1
        person_width = x2 - x1
        frame_height, frame_width = frame.shape[:2]
        
        # تحليل الوضعية
        person_crop = frame[y1:y2, x1:x2]
        if person_crop.size == 0:
            return 'working', 0.5
        
        # تحليل بسيط للوضعية
        # إذا كان الشخص في الجزء العلوي من الإطار = جالس ويعمل
        # إذا كان في الجزء السفلي = قد يكون نائم أو مستلقي
        
        center_y = (y1 + y2) / 2
        relative_position = center_y / frame_height
        
        # تحليل شكل الصندوق
        aspect_ratio = person_width / max(person_height, 1)
        
        # قواعد التصنيف الذكي المحسنة
        if aspect_ratio > 1.3:  # عريض جداً = مستلقي بوضوح
            if relative_position > 0.5:  # في الأسفل
                return 'sleeping', 0.9
            else:
                return 'sleeping', 0.8  # مستلقي في أي مكان
        elif aspect_ratio > 1.1 and relative_position > 0.6:  # عريض قليلاً + أسفل
            if motion_level < 0.03:  # بدون حركة تقريباً
                return 'sleeping', 0.85
            else:
                return 'idle', 0.7
        elif relative_position < 0.3:  # في الأعلى جداً = جالس منتصب
            if motion_level > 0.08:
                return 'working', 0.85
            else:
                return 'working', 0.7  # افتراض العمل للجالس
        elif relative_position > 0.75:  # في الأسفل جداً
            if motion_level < 0.05:
                return 'sleeping', 0.8
            else:
                return 'idle', 0.6
        else:  # في الوسط
            if motion_level > 0.12:
                return 'working', 0.8
            elif motion_level < 0.03:
                # تحليل إضافي للنوم
                if aspect_ratio > 0.9 and relative_position > 0.5:
                    return 'sleeping', 0.7
                else:
                    return 'idle', 0.6
            else:
                return 'working', 0.75
    
    def process_video(
        self,
        input_path: str,
        output_path: str,
        frame_skip: int = 3,
        max_duration: int = 30,
        task_id: Optional[str] = None,
        enable_progress_tracking: bool = True
    ) -> Dict[str, Any]:
        """معالجة ذكية للفيديو"""
        start_time = time.time()
        logger.info(f"🧠 بدء المعالجة الذكية: {input_path}")
        
        # فتح الفيديو
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            return {"success": False, "error": "فشل فتح الفيديو"}
        
        # معلومات الفيديو
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # حجم الإخراج محسن
        output_width = min(width, 720)
        output_height = int(height * (output_width / width))
        
        logger.info(f"📊 فيديو: {total_frames} إطار، {fps:.1f} FPS، إخراج: {output_width}x{output_height}")
        
        # إعداد كاتب الفيديو
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (output_width, output_height))
        
        # متغيرات التتبع
        person_data = {}
        frame_num = 0
        processed_frames = 0
        prev_boxes = {}  # لحساب الحركة
        
        # معالجة ذكية
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
            
            # تخطي الإطارات
            if frame_num % frame_skip != 0:
                continue
            
            processed_frames += 1
            
            # تصغير للمعالجة إذا لزم الأمر
            processing_frame = frame
            if frame.shape[1] > 720:
                scale = 720 / frame.shape[1]
                new_width = int(frame.shape[1] * scale)
                new_height = int(frame.shape[0] * scale)
                processing_frame = cv2.resize(frame, (new_width, new_height))
            
            # كشف الأشخاص
            if self.person_detector:
                detections = self.person_detector.detect(processing_frame)
                
                # تتبع
                tracked_objects = self.tracker.update(detections)
                
                # معالجة كل شخص
                for track_id, track_data in tracked_objects.items():
                    x1, y1, x2, y2 = track_data['box']
                    conf = 0.8
                    
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
                    if self.face_recognizer and person_data[track_id]['name'] == 'Unknown':
                        try:
                            person_crop = processing_frame[y1:y2, x1:x2]
                            if person_crop.size > 0:
                                faces = self.face_recognizer.detect_faces(person_crop)
                                if faces:
                                    best_face = max(faces, key=lambda f: f.get('det_score', 0.0))
                                    if best_face.get('det_score', 0.0) > 0.5:  # عتبة جودة
                                        matches = self.face_recognizer.recognize_face(best_face['embedding'])
                                        if matches and matches[0]['similarity'] > 0.6:  # عتبة تشابه
                                            person_data[track_id]['name'] = matches[0]['name']
                                            logger.info(f"✓ تم التعرف على الشخص {track_id}: {matches[0]['name']}")
                        except Exception as e:
                            if processed_frames % 100 == 0:
                                logger.debug(f"خطأ في التعرف على الوجه: {e}")
                    
                    # حساب الحركة
                    motion_level = 0.0
                    if track_id in prev_boxes:
                        prev_x1, prev_y1, prev_x2, prev_y2 = prev_boxes[track_id]
                        dx = abs(x1 - prev_x1) + abs(x2 - prev_x2)
                        dy = abs(y1 - prev_y1) + abs(y2 - prev_y2)
                        motion_level = (dx + dy) / max(processing_frame.shape[1], 1)
                    prev_boxes[track_id] = (x1, y1, x2, y2)
                    
                    # كشف النشاط الذكي
                    if self.activity_detector:
                        try:
                            # كشف الأشياء للسياق
                            yolo_detections = []
                            try:
                                results = self.person_detector.model.predict(
                                    processing_frame, conf=0.3, classes=None, verbose=False
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
                                frame=processing_frame,
                                person_box=(x1, y1, x2, y2),
                                track_history={},
                                yolo_detections=yolo_detections,
                                track_id=track_id,
                                curr_time=current_time
                            )
                            activity = result.activity
                            confidence = result.confidence
                            
                        except Exception as e:
                            # التصنيف الذكي كبديل
                            activity, confidence = self._classify_activity_smart(
                                (x1, y1, x2, y2), processing_frame, motion_level
                            )
                            if processed_frames % 50 == 0:
                                logger.debug(f"استخدام التصنيف الذكي: {e}")
                    else:
                        # التصنيف الذكي
                        activity, confidence = self._classify_activity_smart(
                            (x1, y1, x2, y2), processing_frame, motion_level
                        )
                    
                    # حفظ النشاط
                    person_data[track_id]['activities'].append((current_time, activity))
                    
                    # حفظ snapshot
                    if person_data[track_id]['snapshot'] is None:
                        try:
                            person_crop = processing_frame[y1:y2, x1:x2]
                            if person_crop.size > 0:
                                snapshot_dir = Path("web_app/static/uploads/test_videos/snapshots")
                                snapshot_dir.mkdir(parents=True, exist_ok=True)
                                snapshot_name = f"person_{track_id}_{int(start_time)}.jpg"
                                snapshot_path = snapshot_dir / snapshot_name
                                cv2.imwrite(str(snapshot_path), person_crop)
                                person_data[track_id]['snapshot'] = f"uploads/test_videos/snapshots/{snapshot_name}"
                        except Exception:
                            pass
                    
                    # رسم على الإطار
                    cv2.rectangle(processing_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    text = f"ID:{track_id} | {activity} ({confidence:.2f})"
                    cv2.putText(processing_frame, text, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # تصغير للإخراج
            if processing_frame.shape[1] != output_width:
                processing_frame = cv2.resize(processing_frame, (output_width, output_height))
            
            # كتابة الإطار
            out.write(processing_frame)
            
            # تقرير التقدم
            if processed_frames % 30 == 0:
                progress = min(95, (current_time / max_duration) * 100) if max_duration > 0 else (frame_num / total_frames) * 100
                logger.info(f"🧠 ذكي: {progress:.0f}% ({processed_frames} إطار)")
        
        # إنهاء المعالجة
        cap.release()
        out.release()
        
        processing_time = time.time() - start_time
        logger.info(f"✅ انتهت المعالجة الذكية في {processing_time:.1f} ثانية")
        
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
                'sleeping_duration': activity_durations.get('sleeping', 0.0),
                'idle_duration': activity_durations.get('idle', 0.0)
            }
            
            statistics.append(person_stats)
            
            logger.info(f"👤 {track_id}: {top_activity} ({person_stats['duration']:.1f}s) - عمل:{activity_durations.get('working', 0):.1f}s نوم:{activity_durations.get('sleeping', 0):.1f}s")
        
        return {
            "success": True,
            "processing_time": round(processing_time, 2),
            "frames_processed": processed_frames,
            "total_frames": total_frames,
            "statistics": statistics,
            "output_path": output_path
        }
