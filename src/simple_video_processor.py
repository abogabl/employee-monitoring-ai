"""
معالج فيديو مبسط جداً بدون تعقيدات
يستخدم time-based tracking بدلاً من frame-based
"""
from __future__ import annotations
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
import cv2
import numpy as np

from .detection_tracking import PersonDetector, PersonTracker
from .deep_sort_tracker import DeepSortTracker
from .face_recognition_system import FaceRecognitionSystem
from .simple_activity_detector import SimpleActivityDetector
from .utils import crop_person, draw_text_with_background

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("simple_video_processor")


class SimpleVideoProcessor:
    """معالج فيديو مبسط جداً"""
    
    def __init__(
        self,
        device: str = "cpu",
        imgsz: int = 640,
        conf_threshold: float = 0.5,
        enable_face_recognition: bool = True,
        enable_activity_recognition: bool = True,
        detection_only: bool = False
    ):
        self.device = device
        self.imgsz = imgsz
        self.conf_threshold = conf_threshold
        self.enable_face = enable_face_recognition
        self.enable_activity = enable_activity_recognition
        self.detection_only = bool(detection_only)
        
        # تهيئة المكونات
        logger.info("تهيئة المعالج المبسط...")
        
        try:
            self.person_detector = PersonDetector(
                model_size="n",
                device=device,
                imgsz=int(imgsz),  # استخدام القيمة الممررة مباشرة
                conf=max(float(conf_threshold), 0.25)
            )
            logger.info("✓ تم تهيئة كاشف الأشخاص")
        except Exception as e:
            logger.error(f"فشل تهيئة كاشف الأشخاص: {e}")
            self.person_detector = None
        
        if not self.detection_only:
            # استخدام PersonTracker (سريع على CPU)
            # DeepSORT بطيء جداً على CPU، يحتاج GPU
            self.tracker = PersonTracker(max_disappeared=90, max_distance=150.0)
            logger.info("✓ تم تهيئة PersonTracker (max_distance=150, max_disappeared=90)")
        else:
            self.tracker = None
        
        if enable_face_recognition:
            try:
                self.face_recognizer = FaceRecognitionSystem()
                logger.info("✓ تم تهيئة التعرف على الوجوه")
            except Exception as e:
                logger.warning(f"فشل التعرف على الوجوه: {e}")
                self.face_recognizer = None
        else:
            self.face_recognizer = None
        
        if enable_activity_recognition:
            try:
                self.activity_detector = SimpleActivityDetector(
                    max_distance=300,
                    motion_window=5,
                    smoothing_method='none'  # تعطيل Motion Smoothing مؤقتاً
                )
                logger.info("✓ تم تهيئة كاشف الأنشطة")
            except Exception as e:
                logger.warning(f"فشل كاشف الأنشطة: {e}")
                self.activity_detector = None
        else:
            self.activity_detector = None
        
        logger.info("✓ المعالج المبسط جاهز")
    
    def process_video(
        self,
        input_path: str,
        output_path: str,
        frame_skip: int = 2,
        max_duration: int = -1
    ) -> Dict[str, Any]:
        """معالجة الفيديو بالطريقة المبسطة"""
        start_time = time.time()
        
        # فتح الفيديو
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            return {'success': False, 'error': 'فشل فتح الفيديو'}
        
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            logger.info(f"📹 الفيديو: {width}x{height}, {fps:.1f}fps, {total_frames} إطار")
            
            # إعداد الفيديو الناتج
            out = cv2.VideoWriter(
                output_path.replace('.mp4', '.avi'),
                cv2.VideoWriter_fourcc(*'XVID'),
                fps,
                (width, height)
            )
            
            # بيانات التتبع المبسطة
            person_data = {}  # track_id -> {'activities': [(time, activity), ...], 'first_time': time, 'last_time': time}
            
            frame_num = 0
            processed_frames = 0
            
            # حساب الحد الأقصى للإطارات
            if max_duration > 0:
                max_frames = int(max_duration * fps)
            else:
                max_frames = total_frames
            
            logger.info(f"⏱️ سيتم معالجة حتى {max_frames} إطار (max_duration={max_duration}s)")
            
            # timeout للأمان (15 دقيقة للفيديوهات الطويلة)
            timeout_seconds = max_duration * 2 if max_duration > 0 else 900
            processing_start = time.time()
            
            while cap.isOpened() and frame_num < max_frames:
                # فحص timeout
                if time.time() - processing_start > timeout_seconds:
                    logger.warning(f"⚠️ تم تجاوز الوقت المحدد ({timeout_seconds}s)، إيقاف المعالجة")
                    break
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_num += 1
                
                # تخطي الإطارات حسب frame_skip
                if frame_skip > 0 and frame_num % (frame_skip + 1) != 0:
                    continue
                
                current_time = frame_num / fps  # الوقت بالثواني
                processed_frames += 1
                
                # الكشف عن الأشخاص
                if self.person_detector:
                    detections = self.person_detector.detect(frame)
                    # Log كل 30 إطار لمتابعة التقدم
                    if frame_num % 30 == 0:
                        logger.info(f"🔍 Frame {frame_num}/{max_frames}: كشف {len(detections)} شخص")
                else:
                    detections = []
                
                # التتبع
                if not self.detection_only and self.tracker:
                    tracker_detections = [
                        {'box': det.get('box', det.get('bbox', (0,0,0,0))), 'confidence': det.get('conf', det.get('confidence', 0.8))}
                        for det in detections
                    ]
                    tracked_persons = list(self.tracker.update(tracker_detections).items())
                else:
                    tracked_persons = [(i+1, {'box': det.get('box', det.get('bbox', (0,0,0,0)))}) for i, det in enumerate(detections)]
                
                # معالجة كل شخص
                for track_id, person_info in tracked_persons:
                    box = person_info['box']
                    x1, y1, x2, y2 = map(int, box)
                    
                    # تهيئة بيانات الشخص
                    if track_id not in person_data:
                        person_data[track_id] = {
                            'activities': [],
                            'first_time': current_time,
                            'last_time': current_time,
                            'name': 'Unknown',
                            'snapshot': None
                        }
                        logger.info(f"✨ شخص جديد! Track ID={track_id}, Frame={frame_num}, Time={current_time:.2f}s")
                    
                    # تحديث الوقت
                    person_data[track_id]['last_time'] = current_time
                    
                    # التعرف على النشاط
                    activity = 'unknown'
                    if self.activity_detector and self.person_detector:
                        try:
                            # كشف الأشياء (كل الأشياء المرتبطة بالعمل)
                            yolo_detections = []
                            if hasattr(self.person_detector, 'model') and self.person_detector.model:
                                obj_classes = [62, 63, 66, 67, 72]  # tv, laptop, keyboard, cell phone, monitor
                                results = self.person_detector.model.predict(
                                    frame,
                                    imgsz=640,
                                    conf=0.25,
                                    device=self.person_detector.device,
                                    classes=obj_classes,
                                    verbose=False
                                )
                                if results and results[0].boxes is not None:
                                    obj_names = {62: 'tv', 63: 'laptop', 66: 'keyboard', 67: 'cell phone', 72: 'monitor'}
                                    for b in results[0].boxes:
                                        x1_obj, y1_obj, x2_obj, y2_obj = map(int, b.xyxy[0].tolist())
                                        cls_obj = int(b.cls[0])
                                        yolo_detections.append({
                                            'box': (x1_obj, y1_obj, x2_obj, y2_obj),
                                            'class': cls_obj,
                                            'name': obj_names.get(cls_obj, f'class_{cls_obj}')
                                        })
                            
                            # كشف النشاط
                            activity, confidence = self.activity_detector.detect_activity(
                                person_box=(x1, y1, x2, y2),
                                track_id=track_id,
                                yolo_detections=yolo_detections,
                                frame_time=current_time
                            )
                            
                            # تقليل logging لتسريع المعالجة: فقط كل 60 إطار
                            if frame_num % 60 == 0:
                                logger.info(f"🎯 Frame {frame_num}, Person {track_id}: {activity} ({confidence:.2f}), Objects={len(yolo_detections)}")
                            
                        except Exception as e:
                            logger.warning(f"خطأ في كشف النشاط: {e}")
                    elif self.activity_detector:
                        # fallback بدون كشف أشياء
                        try:
                            activity, confidence = self.activity_detector.detect_activity(
                                person_box=(x1, y1, x2, y2),
                                track_id=track_id,
                                yolo_detections=[],
                                frame_time=current_time
                            )
                            if frame_num % 60 == 0:
                                logger.info(f"🎯 Frame {frame_num}, Person {track_id}: {activity} ({confidence:.2f}) [no objects]")
                        except Exception as e:
                            logger.warning(f"خطأ في كشف النشاط بدون أشياء: {e}")
                    
                    # حفظ النشاط مع الوقت
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
                            logger.debug(f"خطأ في حفظ snapshot: {e}")
                    
                    # رسم على الإطار
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, f"ID:{track_id} {activity}", (x1, y1-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # كتابة الإطار
                out.write(frame)
                
                # تقدم كل 30 إطار
                if frame_num % 30 == 0:
                    logger.info(f"⏳ معالجة: {frame_num}/{max_frames} إطار ({100*frame_num/max_frames:.1f}%)")
        
        finally:
            cap.release()
            out.release()
        
        processing_time = time.time() - start_time
        
        logger.info(f"✅ انتهت المعالجة: {frame_num} إطار في {processing_time:.2f}s")
        
        # إحصائيات الكشف
        total_detections = sum(len(data['activities']) for data in person_data.values())
        detection_rate = (total_detections / frame_num * 100) if frame_num > 0 else 0
        logger.info(f"📊 إحصائيات الكشف:")
        logger.info(f"   - إجمالي الإطارات: {frame_num}")
        logger.info(f"   - إطارات مع كشف: {total_detections}")
        logger.info(f"   - نسبة الكشف: {detection_rate:.1f}%")
        logger.info(f"   - عدد المسارات: {len(person_data)}")
        
        # دمج المسارات المكررة (إذا كان هناك شخص واحد فقط)
        if len(person_data) > 1:
            logger.info(f"⚠️ تم كشف {len(person_data)} مسارات، محاولة الدمج...")
            person_data = self._merge_duplicate_tracks(person_data)
            logger.info(f"✓ بعد الدمج: {len(person_data)} شخص")
        
        # حساب النتائج
        return self._calculate_results(person_data, fps, processing_time, processed_frames, output_path)
    
    def _merge_duplicate_tracks(self, person_data: Dict) -> Dict:
        """دمج المسارات المكررة لنفس الشخص"""
        if len(person_data) <= 1:
            return person_data
        
        # دمج كل المسارات في مسار واحد (ID=1)
        merged_data = {
            1: {
                'activities': [],
                'first_time': float('inf'),
                'last_time': 0.0,
                'name': 'Unknown',
                'snapshot': None
            }
        }
        
        for track_id, data in person_data.items():
            # دمج الأنشطة
            merged_data[1]['activities'].extend(data['activities'])
            
            # تحديث الأوقات
            merged_data[1]['first_time'] = min(merged_data[1]['first_time'], data['first_time'])
            merged_data[1]['last_time'] = max(merged_data[1]['last_time'], data['last_time'])
            
            # استخدام أول snapshot
            if merged_data[1]['snapshot'] is None and data['snapshot']:
                merged_data[1]['snapshot'] = data['snapshot']
        
        # ترتيب الأنشطة حسب الوقت
        merged_data[1]['activities'].sort(key=lambda x: x[0])
        
        return merged_data
    
    def _calculate_results(self, person_data: Dict, fps: float, processing_time: float, 
                          processed_frames: int, output_path: str) -> Dict[str, Any]:
        """حساب النتائج بالطريقة المبسطة"""
        logger.info("\n" + "="*80)
        logger.info("📊 حساب النتائج المبسطة:")
        logger.info("="*80)
        
        statistics = []
        activity_counts = {}
        
        for track_id, data in person_data.items():
            logger.info(f"\n🔍 Person {track_id}:")
            logger.info(f"   - Time range: {data['first_time']:.2f}s to {data['last_time']:.2f}s")
            logger.info(f"   - Total activities recorded: {len(data['activities'])}")
            
            # عرض أول 5 أنشطة للتشخيص
            if data['activities']:
                logger.info(f"   - First 5 activities: {data['activities'][:5]}")
            
            # حساب مدة كل نشاط بالطريقة الجديدة
            activity_durations = {}
            if data['activities']:
                # تجميع الأنشطة حسب النوع
                activity_groups = {}
                for time_val, activity in data['activities']:
                    if activity != 'unknown':
                        if activity not in activity_groups:
                            activity_groups[activity] = []
                        activity_groups[activity].append(time_val)
                
                # حساب المدة لكل نشاط
                for activity, times in activity_groups.items():
                    if times:
                        # الطريقة الصحيحة: عدد المرات × الوقت بين الإطارات
                        num_occurrences = len(times)
                        duration = num_occurrences / fps  # كل occurrence = 1 إطار
                        activity_durations[activity] = duration
                        
                        first_time = min(times)
                        last_time = max(times)
                        logger.info(f"   ✓ {activity}: {num_occurrences} occurrences, {first_time:.2f}s-{last_time:.2f}s, duration={duration:.2f}s")
            
            # إضافة للإحصائيات
            working_duration = activity_durations.get('working', 0.0)
            sleeping_duration = activity_durations.get('sleeping', 0.0)
            phone_duration = activity_durations.get('on_phone', 0.0)
            
            # حساب المدة الإجمالية: عدد الإطارات المسجلة / fps
            total_duration = len(data['activities']) / fps if data['activities'] else 0.0
            
            logger.info(f"   - Total duration: {total_duration:.2f}s (from {len(data['activities'])} frames)")
            
            # تحديد النشاط الأكثر
            top_activity = 'unknown'
            if activity_durations:
                top_activity = max(activity_durations.keys(), key=lambda k: activity_durations[k])
            
            statistics.append({
                'name': data['name'],
                'track_id': track_id,
                'count': len(data['activities']),
                'top_activity': top_activity,
                'avg_confidence': 0.8,  # ثابت للتبسيط
                'working_duration': working_duration,
                'sleeping_duration': sleeping_duration,
                'phone_duration': phone_duration,
                'duration': total_duration,
                'snapshot': data['snapshot']
            })
            
            # تحديث العدادات
            for activity in activity_durations:
                activity_counts[activity] = activity_counts.get(activity, 0) + activity_durations[activity]
        
        logger.info(f"\n📌 النتائج النهائية:")
        for stat in statistics:
            logger.info(f"   - Person {stat['track_id']}: Working={stat['working_duration']:.2f}s, Total={stat['duration']:.2f}s")
        
        return {
            'success': True,
            'total_persons': len(person_data),
            'known_persons': 0,
            'total_activities': sum(activity_counts.values()),
            'activity_breakdown': activity_counts,
            'processing_time': processing_time,
            'total_frames': processed_frames,
            'processed_frames': processed_frames,
            'details': [],
            'statistics': statistics,
            'debug_image': None,
            'output_video': output_path.replace('.mp4', '.avi')
        }
