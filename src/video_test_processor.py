"""
معالج اختبار الفيديو مع دمج AI كامل
يستخدم جميع مكونات النظام الحقيقية للحصول على أفضل دقة
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Optional

import cv2
import numpy as np

from .detection_tracking import PersonDetector, PersonTracker
from .face_recognition_system import FaceRecognitionSystem
from .activity_recognition import ActivityRecognizer
from .utils import crop_person, draw_text_with_background

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("video_test_processor")


class VideoTestProcessor:
    """معالج فيديو اختبار متكامل مع AI"""
    
    def __init__(
        self,
        device: str = "cpu",
        imgsz: int = 640,
        conf_threshold: float = 0.5,
        enable_face_recognition: bool = True,
        enable_activity_recognition: bool = True
    ):
        self.device = device
        self.imgsz = imgsz
        self.conf_threshold = conf_threshold
        self.enable_face = enable_face_recognition
        self.enable_activity = enable_activity_recognition
        self.hog_detector = None
        # هدف قياس للكشف لتسريع الأداء (نكتشف على عرض 640 كحد أقصى)
        self.detect_target_width = 640
        
        # تهيئة المكونات
        logger.info("تهيئة معالج الفيديو...")
        
        try:
            self.person_detector = PersonDetector(
                device=device,
                imgsz=imgsz,
                conf_threshold=conf_threshold
            )
            logger.info("✓ تم تهيئة كاشف الأشخاص (YOLO)")
        except Exception as e:
            logger.warning(f"فشل تهيئة YOLO: {e}")
            logger.info("سيتم استخدام HOG Detector البديل...")
            try:
                import cv2
                self.hog_detector = cv2.HOGDescriptor()
                self.hog_detector.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
                self.person_detector = "HOG"
                logger.info("✓ تم تهيئة HOG Detector")
            except Exception as e2:
                logger.error(f"فشل تهيئة HOG أيضاً: {e2}")
                self.person_detector = None
                self.hog_detector = None
        
        self.tracker = PersonTracker()
        logger.info("✓ تم تهيئة نظام التتبع")
        
        if enable_face_recognition:
            try:
                self.face_recognizer = FaceRecognitionSystem()
                logger.info("✓ تم تهيئة نظام التعرف على الوجوه")
            except Exception as e:
                logger.warning(f"فشل تهيئة التعرف على الوجوه: {e}")
                self.face_recognizer = None
        else:
            self.face_recognizer = None
        
        if enable_activity_recognition:
            try:
                self.activity_recognizer = ActivityRecognizer()
                logger.info("✓ تم تهيئة نظام التعرف على الأنشطة")
            except Exception as e:
                logger.warning(f"فشل تهيئة التعرف على الأنشطة: {e}")
                self.activity_recognizer = None
        else:
            self.activity_recognizer = None
        
        logger.info("✓ جاهز للمعالجة")
    
    def process_video(
        self,
        input_path: str,
        output_path: str,
        frame_skip: int = 2,
        max_duration: int = -1
    ) -> Dict[str, Any]:
        """
        معالجة فيديو كامل مع AI
        
        Args:
            input_path: مسار الفيديو المدخل
            output_path: مسار الفيديو الناتج
            frame_skip: عدد الإطارات المتخطاة (1 = كل إطار)
            max_duration: الحد الأقصى للمدة بالثواني (-1 = بدون حد)
        
        Returns:
            قاموس يحتوي على النتائج والإحصائيات
        """
        logger.info(f"بدء معالجة الفيديو: {input_path}")
        start_time = time.time()
        
        # فتح الفيديو
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"فشل فتح الفيديو: {input_path}")
        
        # معلومات الفيديو
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 25
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        logger.info(f"معلومات الفيديو: {width}x{height} @ {fps}fps, {total_frames} إطارات")
        
        # إنشاء الفيديو الناتج
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        # إحصائيات
        frame_count = 0
        processed_count = 0
        max_frames = fps * max_duration if max_duration > 0 else float('inf')
        # حد أقصى للوقت (ثواني) لتجربة سريعة
        max_wall_time = 90
        
        # تتبع البيانات
        track_data = defaultdict(lambda: {
            'name': 'Unknown',
            'frames': [],
            'activities': [],
            'confidences': [],
            'first_seen': 0,
            'last_seen': 0
        })
        
        all_detections = []
        
        try:
            while cap.isOpened() and frame_count < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # نسخة للرسم
                display_frame = frame.copy()

                # تحديد عامل التصغير للكشف لتسريع الأداء
                scale = 1.0
                if width > self.detect_target_width:
                    scale = self.detect_target_width / float(width)
                det_frame = frame
                if scale < 1.0:
                    det_w = int(width * scale)
                    det_h = int(height * scale)
                    det_frame = cv2.resize(frame, (det_w, det_h), interpolation=cv2.INTER_LINEAR)
                
                # معالجة إطارات محددة فقط
                if frame_count % frame_skip == 0:
                    processed_count += 1
                    timestamp = frame_count / fps
                    
                    # 1. كشف الأشخاص
                    detections = []
                    if self.person_detector == "HOG":
                        # استخدام HOG Detector
                        try:
                            # زيادة frame_skip تلقائياً مع HOG لتسريع الأداء
                            if frame_skip < 5:
                                frame_skip = 5
                            gray = cv2.cvtColor(det_frame, cv2.COLOR_BGR2GRAY)
                            boxes, weights = self.hog_detector.detectMultiScale(
                                gray,
                                winStride=(8, 8),
                                padding=(4, 4),
                                scale=1.05
                            )
                            # HOG يعطي boxes و weights
                            for (x, y, w, h) in boxes:
                                # إعادة القياس إلى أبعاد الإطار الأصلي
                                if scale < 1.0:
                                    x = int(x / scale); y = int(y / scale)
                                    w = int(w / scale); h = int(h / scale)
                                detections.append({
                                    'bbox': [x, y, x+w, y+h],
                                    'confidence': 0.8  # HOG لا يعطي confidence دقيق
                                })
                        except Exception as e:
                            logger.warning(f"خطأ في HOG: {e}")
                    elif self.person_detector:
                        # استخدام YOLO Detector
                        try:
                            # إن أمكن، نمرر الإطار المصغر
                            dets = self.person_detector.detect(det_frame) or []
                            detections = []
                            for det in dets:
                                # مصادر YOLO تُرجع 'box' و 'conf'
                                if 'bbox' in det:
                                    x1, y1, x2, y2 = det['bbox']
                                else:
                                    x1, y1, x2, y2 = det.get('box', [0,0,0,0])
                                # إعادة القياس للصناديق إذا تم التصغير
                                if scale < 1.0:
                                    x1 = int(x1 / scale); y1 = int(y1 / scale)
                                    x2 = int(x2 / scale); y2 = int(y2 / scale)
                                detections.append({
                                    'bbox': [x1, y1, x2, y2],
                                    'confidence': float(det.get('confidence', det.get('conf', 0.0)))
                                })
                        except Exception as e:
                            logger.warning(f"خطأ في الكشف: {e}")
                    
                    # 2. تحويل detections لـ tracker format
                    # PersonTracker يتوقع 'box' مش 'bbox'
                    tracker_detections = []
                    for det in detections:
                        tracker_detections.append({
                            'box': det['bbox'],
                            'confidence': det.get('confidence', 0.8)
                        })
                    
                    # 3. تتبع (بدون frame parameter)
                    if tracker_detections:
                        tracked_dict = self.tracker.update(tracker_detections)
                        tracked_persons = list(tracked_dict.items())
                    else:
                        tracked_persons = []
                    
                    # 4. معالجة كل شخص
                    for track_id, person_data in tracked_persons:
                        bbox = person_data.get('box', [0, 0, 10, 10])
                        x1, y1, x2, y2 = map(int, bbox)
                        
                        # التأكد من أن المربع داخل الإطار
                        x1 = max(0, x1)
                        y1 = max(0, y1)
                        x2 = min(width, x2)
                        y2 = min(height, y2)
                        
                        # اقتصاص الشخص
                        person_crop = crop_person(frame, bbox)
                        
                        # التعرف على الوجه
                        person_name = "Unknown"
                        face_conf = 0.0
                        if self.face_recognizer and person_crop is not None:
                            try:
                                face_result = self.face_recognizer.recognize_face(person_crop)
                                if face_result:
                                    person_name = face_result.get('name', 'Unknown')
                                    face_conf = face_result.get('confidence', 0.0)
                            except Exception as e:
                                logger.debug(f"خطأ في التعرف على الوجه: {e}")
                        
                        # التعرف على النشاط
                        activity = "unknown"
                        activity_conf = 0.0
                        if self.activity_recognizer and person_crop is not None:
                            try:
                                activity_result = self.activity_recognizer.recognize(person_crop)
                                if activity_result:
                                    activity = activity_result.get('activity', 'unknown')
                                    activity_conf = activity_result.get('confidence', 0.0)
                            except Exception as e:
                                logger.debug(f"خطأ في التعرف على النشاط: {e}")
                        
                        # حفظ البيانات
                        track_data[track_id]['name'] = person_name if person_name != "Unknown" else track_data[track_id]['name']
                        track_data[track_id]['frames'].append(frame_count)
                        track_data[track_id]['activities'].append(activity)
                        track_data[track_id]['confidences'].append(max(face_conf, activity_conf))
                        track_data[track_id]['last_seen'] = frame_count
                        if track_data[track_id]['first_seen'] == 0:
                            track_data[track_id]['first_seen'] = frame_count
                        
                        # حفظ التفاصيل
                        all_detections.append({
                            'frame': frame_count,
                            'timestamp': timestamp,
                            'track_id': track_id,
                            'person': person_name,
                            'activity': activity,
                            'face_confidence': face_conf,
                            'activity_confidence': activity_conf
                        })
                        
                        # الرسم على الإطار
                        # اختيار اللون حسب النشاط
                        color_map = {
                            'working': (0, 255, 0),      # أخضر
                            'on_phone': (0, 165, 255),   # برتقالي
                            'sleeping': (0, 0, 255),     # أحمر
                            'unknown': (255, 255, 255)   # أبيض
                        }
                        color = color_map.get(activity, (128, 128, 128))
                        
                        # رسم المربع
                        cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
                        
                        # إعداد النصوص
                        texts = []
                        if person_name != "Unknown":
                            texts.append(f"{person_name} ({face_conf:.2f})")
                        else:
                            texts.append(f"Person #{track_id}")
                        
                        # ترجمة الأنشطة للعربية
                        activity_ar = {
                            'working': 'يعمل',
                            'on_phone': 'على الهاتف',
                            'sleeping': 'نائم',
                            'unknown': 'غير محدد'
                        }.get(activity, activity)
                        
                        texts.append(f"{activity_ar} ({activity_conf:.2f})")
                        
                        # رسم النصوص
                        y_offset = y1 - 10
                        for text in texts:
                            draw_text_with_background(
                                display_frame, text,
                                (x1, y_offset),
                                color=color,
                                font_scale=0.5
                            )
                            y_offset -= 25
                
                # كتابة الإطار
                out.write(display_frame)
                frame_count += 1
                
                # تقدم كل 30 إطار
                if frame_count % 30 == 0:
                    logger.info(f"معالجة: {frame_count}/{min(total_frames, max_frames)} إطار")

                # حد أقصى زمني للحماية من البطء الشديد
                if time.time() - start_time > max_wall_time and processed_count > 0:
                    logger.info("توقف مبكر: تجاوز زمن المعالجة الحد المحدد للتجربة")
                    break
        
        finally:
            cap.release()
            out.release()
        
        processing_time = time.time() - start_time
        logger.info(f"اكتملت المعالجة في {processing_time:.2f} ثانية")
        
        # إعداد النتائج
        return self._prepare_results(
            track_data, all_detections, 
            frame_count, processed_count, 
            processing_time, fps
        )
    
    def _prepare_results(
        self,
        track_data: Dict,
        all_detections: List[Dict],
        total_frames: int,
        processed_frames: int,
        processing_time: float,
        fps: int
    ) -> Dict[str, Any]:
        """تحضير النتائج النهائية"""
        
        # إحصائيات الأشخاص
        unique_persons = set()
        known_persons = set()
        
        for track_id, data in track_data.items():
            name = data['name']
            if name != 'Unknown':
                known_persons.add(name)
            unique_persons.add(track_id)
        
        # إحصائيات الأنشطة
        all_activities = []
        for data in track_data.values():
            all_activities.extend(data['activities'])
        
        activity_counts = defaultdict(int)
        for activity in all_activities:
            activity_counts[activity] += 1
        
        # إحصائيات لكل شخص
        statistics = []
        for track_id, data in track_data.items():
            if data['activities']:
                top_activity = max(set(data['activities']), key=data['activities'].count)
            else:
                top_activity = 'unknown'
            
            avg_confidence = sum(data['confidences']) / len(data['confidences']) if data['confidences'] else 0.0
            
            statistics.append({
                'name': data['name'],
                'track_id': track_id,
                'count': len(data['frames']),
                'top_activity': top_activity,
                'avg_confidence': avg_confidence,
                'duration': (data['last_seen'] - data['first_seen']) / fps
            })
        
        # ترتيب حسب عدد الظهور
        statistics.sort(key=lambda x: x['count'], reverse=True)
        
        # تفاصيل الكشف (أول 50)
        details = []
        for det in all_detections[:50]:
            timestamp_str = f"{int(det['timestamp']//60):02d}:{int(det['timestamp']%60):02d}"
            details.append({
                'person': det['person'] if det['person'] != 'Unknown' else f"Person #{det['track_id']}",
                'timestamp': timestamp_str,
                'activity': det['activity'],
                'confidence': max(det['face_confidence'], det['activity_confidence'])
            })
        
        return {
            'success': True,
            'total_persons': len(unique_persons),
            'known_persons': len(known_persons),
            'total_activities': sum(activity_counts.values()),
            'activity_breakdown': dict(activity_counts),
            'processing_time': processing_time,
            'total_frames': total_frames,
            'processed_frames': processed_frames,
            'details': details,
            'statistics': statistics
        }
