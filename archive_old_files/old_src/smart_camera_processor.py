"""
Smart Camera Processor
معالج كاميرات ذكي يستخدم نفس التحسينات من SmartVideoProcessor
للكاميرات المباشرة مع تتبع الحضور في الوقت الفعلي
"""
from __future__ import annotations
import logging
import time
import threading
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional, Callable
from collections import defaultdict, deque
from datetime import datetime
import cv2
import numpy as np

from .detection_tracking import PersonDetector, PersonTracker
from .face_recognition_system import FaceRecognitionSystem
from .activity_recognition import ActivityRecognizer
from .activity_rules import ActivityRules
from .attendance_manager import AttendanceManager
from .utils import draw_text_with_background

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smart_camera_processor")


class SmartCameraProcessor:
    """معالج كاميرات ذكي مع التحسينات الجديدة"""
    
    def __init__(
        self,
        camera_id: str,
        device: str = "cpu",
        imgsz: int = 416,
        conf_threshold: float = 0.35,
        enable_face_recognition: bool = True,
        enable_activity_recognition: bool = True,
        enable_attendance: bool = True,
        yolo_model: str = "s",  # توازن بين السرعة والدقة
        activity_window: int = 15,
        attendance_manager: Optional[AttendanceManager] = None
    ):
        self.camera_id = camera_id
        self.device = device
        self.imgsz = imgsz
        self.conf_threshold = conf_threshold
        self.enable_face = enable_face_recognition
        self.enable_activity = enable_activity_recognition
        self.enable_attendance = enable_attendance
        
        logger.info(f"تهيئة المعالج الذكي للكاميرا {camera_id}...")
        
        # كاشف الأشخاص المحسن
        try:
            self.person_detector = PersonDetector(
                model_size=yolo_model,
                device=device,
                imgsz=int(imgsz),
                conf=float(conf_threshold),
                iou=0.5
            )
            logger.info(f"✓ كاشف الأشخاص الذكي: yolov8{yolo_model}, imgsz={imgsz}")
        except Exception as e:
            logger.error(f"فشل تهيئة كاشف الأشخاص: {e}")
            self.person_detector = None
        
        # تتبع محسن
        self.tracker = PersonTracker(max_disappeared=45, max_distance=120.0)
        
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
        
        # كشف الأنشطة المحسن
        if enable_activity_recognition:
            try:
                activity_rules = ActivityRules(config_path="config/activity_config.json")
                self.activity_detector = ActivityRecognizer(
                    use_pose=True,
                    use_objects=True,
                    use_motion=True,
                    smoothing_seconds=4.0,
                    fps_hint=20.0,
                    window_size=activity_window,
                    use_ema=True,
                    ema_alpha=0.2,
                    activity_rules=activity_rules
                )
                logger.info("✓ كاشف الأنشطة الذكي مع التنعيم المحسن")
            except Exception as e:
                logger.warning(f"فشل تهيئة كاشف الأنشطة: {e}")
                self.activity_detector = None
        else:
            self.activity_detector = None
        
        # نظام الحضور
        self.attendance_manager = attendance_manager
        if enable_attendance and not attendance_manager:
            try:
                self.attendance_manager = AttendanceManager()
                logger.info("✓ تم تهيئة نظام الحضور")
            except Exception as e:
                logger.warning(f"فشل تهيئة نظام الحضور: {e}")
        
        # بيانات التتبع
        self.person_data = {}
        self.prev_boxes = {}
        self.frame_count = 0
        self.last_attendance_update = time.time()
        self.attendance_interval = 30  # تحديث الحضور كل 30 ثانية
        
        # إحصائيات الأداء
        self.fps_counter = deque(maxlen=30)
        self.processing_times = deque(maxlen=100)
        
        logger.info(f"✓ تم تهيئة المعالج الذكي للكاميرا {camera_id} بنجاح")
    
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
    
    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """معالجة إطار واحد من الكاميرا"""
        start_time = time.time()
        self.frame_count += 1
        current_time = time.time()
        
        # نسخة للعرض
        display_frame = frame.copy()
        
        # تصغير للمعالجة إذا لزم الأمر
        processing_frame = frame
        if frame.shape[1] > 720:
            scale = 720 / frame.shape[1]
            new_width = int(frame.shape[1] * scale)
            new_height = int(frame.shape[0] * scale)
            processing_frame = cv2.resize(frame, (new_width, new_height))
        
        frame_stats = {
            'persons_detected': 0,
            'persons_recognized': 0,
            'activities': defaultdict(int),
            'processing_time': 0.0
        }
        
        # كشف الأشخاص
        if self.person_detector:
            detections = self.person_detector.detect(processing_frame)
            tracked_objects = self.tracker.update(detections)
            
            frame_stats['persons_detected'] = len(tracked_objects)
            
            # معالجة كل شخص
            for track_id, track_data in tracked_objects.items():
                x1, y1, x2, y2 = track_data['box']
                conf = 0.8
                
                # تهيئة بيانات الشخص
                if track_id not in self.person_data:
                    self.person_data[track_id] = {
                        'name': 'Unknown',
                        'activities': [],
                        'first_seen': current_time,
                        'last_seen': current_time,
                        'total_confidence': 0.0,
                        'detection_count': 0,
                        'current_activity': 'idle',
                        'activity_start_time': current_time
                    }
                
                # تحديث بيانات الشخص
                person_info = self.person_data[track_id]
                person_info['last_seen'] = current_time
                person_info['total_confidence'] += conf
                person_info['detection_count'] += 1
                
                # التعرف على الوجه
                if self.face_recognizer and person_info['name'] == 'Unknown':
                    try:
                        person_crop = processing_frame[y1:y2, x1:x2]
                        if person_crop.size > 0:
                            faces = self.face_recognizer.detect_faces(person_crop)
                            if faces:
                                best_face = max(faces, key=lambda f: f.get('det_score', 0.0))
                                if best_face.get('det_score', 0.0) > 0.5:
                                    matches = self.face_recognizer.recognize_face(best_face['embedding'])
                                    if matches and matches[0]['similarity'] > 0.6:
                                        person_info['name'] = matches[0]['name']
                                        frame_stats['persons_recognized'] += 1
                                        logger.info(f"✓ تم التعرف على الشخص {track_id}: {matches[0]['name']}")
                    except Exception as e:
                        if self.frame_count % 100 == 0:
                            logger.debug(f"خطأ في التعرف على الوجه: {e}")
                
                # حساب الحركة
                motion_level = 0.0
                if track_id in self.prev_boxes:
                    prev_x1, prev_y1, prev_x2, prev_y2 = self.prev_boxes[track_id]
                    dx = abs(x1 - prev_x1) + abs(x2 - prev_x2)
                    dy = abs(y1 - prev_y1) + abs(y2 - prev_y2)
                    motion_level = (dx + dy) / max(processing_frame.shape[1], 1)
                self.prev_boxes[track_id] = (x1, y1, x2, y2)
                
                # كشف النشاط
                activity = 'idle'
                activity_conf = 0.5
                
                if self.activity_detector:
                    try:
                        # استخدام كاشف الأنشطة المحسن
                        result = self.activity_detector.process_person(
                            processing_frame,
                            (x1, y1, x2, y2),
                            {},
                            detections,
                            track_id,
                            current_time
                        )
                        activity = result.activity
                        activity_conf = result.confidence
                    except Exception as e:
                        # استخدام التصنيف الذكي كبديل
                        activity, activity_conf = self.smart_classify_activity(
                            x1, y1, x2, y2, 
                            processing_frame.shape[0], 
                            processing_frame.shape[1], 
                            motion_level
                        )
                else:
                    # استخدام التصنيف الذكي
                    activity, activity_conf = self.smart_classify_activity(
                        x1, y1, x2, y2, 
                        processing_frame.shape[0], 
                        processing_frame.shape[1], 
                        motion_level
                    )
                
                # تحديث النشاط الحالي
                if person_info['current_activity'] != activity:
                    person_info['current_activity'] = activity
                    person_info['activity_start_time'] = current_time
                
                frame_stats['activities'][activity] += 1
                
                # رسم المعلومات على الإطار
                self._draw_person_info(
                    display_frame, x1, y1, x2, y2,
                    person_info['name'], activity, activity_conf, track_id
                )
        
        # تحديث الحضور
        if self.enable_attendance and self.attendance_manager:
            if current_time - self.last_attendance_update > self.attendance_interval:
                self._update_attendance()
                self.last_attendance_update = current_time
        
        # حساب الأداء
        processing_time = time.time() - start_time
        self.processing_times.append(processing_time)
        frame_stats['processing_time'] = processing_time
        
        # رسم معلومات الأداء
        self._draw_performance_info(display_frame)
        
        return display_frame, frame_stats
    
    def _draw_person_info(
        self, frame: np.ndarray, 
        x1: int, y1: int, x2: int, y2: int,
        name: str, activity: str, confidence: float, track_id: int
    ):
        """رسم معلومات الشخص على الإطار"""
        # رسم المربع
        color = (0, 255, 0) if name != 'Unknown' else (0, 165, 255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        
        # رسم المعلومات
        info_text = f"ID:{track_id} {name}"
        activity_text = f"{activity} ({confidence:.2f})"
        
        draw_text_with_background(frame, info_text, (x1, y1 - 30), 
                                font_scale=0.6, color=(255, 255, 255), bg_color=color)
        
        activity_color = {
            'working': (0, 255, 0),
            'sleeping': (0, 0, 255),
            'on_phone': (0, 255, 255),
            'idle': (128, 128, 128)
        }.get(activity, (255, 255, 255))
        
        draw_text_with_background(frame, activity_text, (x1, y1 - 10),
                                font_scale=0.5, color=(255, 255, 255), bg_color=activity_color)
    
    def _draw_performance_info(self, frame: np.ndarray):
        """رسم معلومات الأداء"""
        if self.processing_times:
            avg_time = np.mean(self.processing_times)
            fps = 1.0 / avg_time if avg_time > 0 else 0
            
            info_text = f"FPS: {fps:.1f} | Persons: {len(self.person_data)}"
            draw_text_with_background(frame, info_text, (10, 30),
                                    font_scale=0.7, color=(255, 255, 255), bg_color=(0, 0, 0))
    
    def _update_attendance(self):
        """تحديث سجلات الحضور"""
        if not self.attendance_manager:
            return
        
        current_time = datetime.now()
        
        for track_id, person_info in self.person_data.items():
            if person_info['name'] != 'Unknown':
                # تسجيل الحضور
                try:
                    self.attendance_manager.record_attendance(
                        employee_name=person_info['name'],
                        camera_id=self.camera_id,
                        timestamp=current_time,
                        activity=person_info['current_activity']
                    )
                except Exception as e:
                    logger.error(f"خطأ في تسجيل الحضور: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """الحصول على إحصائيات المعالجة"""
        current_time = time.time()
        
        stats = {
            'camera_id': self.camera_id,
            'total_persons': len(self.person_data),
            'known_persons': sum(1 for p in self.person_data.values() if p['name'] != 'Unknown'),
            'frame_count': self.frame_count,
            'avg_fps': 1.0 / np.mean(self.processing_times) if self.processing_times else 0,
            'persons': []
        }
        
        for track_id, person_info in self.person_data.items():
            duration = current_time - person_info['first_seen']
            avg_conf = person_info['total_confidence'] / max(person_info['detection_count'], 1)
            
            stats['persons'].append({
                'track_id': track_id,
                'name': person_info['name'],
                'duration': duration,
                'avg_confidence': avg_conf,
                'current_activity': person_info['current_activity'],
                'last_seen': person_info['last_seen']
            })
        
        return stats
    
    def cleanup(self):
        """تنظيف الموارد"""
        logger.info(f"تنظيف موارد المعالج للكاميرا {self.camera_id}")
        if hasattr(self, 'person_detector') and self.person_detector:
            del self.person_detector
        if hasattr(self, 'face_recognizer') and self.face_recognizer:
            del self.face_recognizer
        if hasattr(self, 'activity_detector') and self.activity_detector:
            del self.activity_detector
