"""
Full Video Processor - Combines tracking, face recognition, and activity detection
Complete Pipeline Implementation
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Optional
import time
import logging
from collections import defaultdict

from .tracker import PersonTracker
from .face_system import FaceRecognitionSystem
from .activity_detector import ActivityDetector

logger = logging.getLogger(__name__)


class FullVideoProcessor:
    """معالج فيديو كامل مع كل الميزات"""
    
    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        conf_threshold: float = 0.5,
        tracker_type: str = "botsort",
        frame_skip: int = 1,
        enable_face: bool = True,
        enable_activity: bool = True
    ):
        """
        تهيئة المعالج الكامل
        
        Args:
            model_path: مسار نموذج YOLO
            conf_threshold: عتبة الثقة
            tracker_type: نوع المتتبع
            frame_skip: تخطي الإطارات
            enable_face: تفعيل التعرف على الوجوه
            enable_activity: تفعيل كشف الأنشطة
        """
        # تتبع الأشخاص
        self.tracker = PersonTracker(model_path, conf_threshold, tracker_type)
        self.frame_skip = max(1, frame_skip)
        
        # التعرف على الوجوه
        self.face_system = None
        if enable_face:
            try:
                self.face_system = FaceRecognitionSystem()
                logger.info("✓ تم تفعيل التعرف على الوجوه")
            except Exception as e:
                logger.warning(f"⚠️ فشل تفعيل التعرف على الوجوه: {e}")
        
        # كشف الأنشطة
        self.activity_detector = None
        if enable_activity:
            try:
                self.activity_detector = ActivityDetector()
                logger.info("✓ تم تفعيل كشف الأنشطة")
            except Exception as e:
                logger.warning(f"⚠️ فشل تفعيل كشف الأنشطة: {e}")
        
        # ألوان للرسم
        self.colors = [
            (0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0),
            (255, 0, 255), (0, 255, 255), (128, 255, 0), (255, 128, 0)
        ]
        
        logger.info(f"✓ تم تهيئة المعالج الكامل")
    
    def process_video(
        self,
        input_path: str,
        output_path: str,
        max_duration: Optional[int] = None
    ) -> Dict:
        """
        معالجة فيديو كامل
        """
        start_time = time.time()
        
        # فتح الفيديو
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"لا يمكن فتح الفيديو: {input_path}")
        
        # معلومات الفيديو
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        
        logger.info(f"📹 الفيديو: {width}x{height}, {fps:.1f} FPS, {duration:.1f}s")
        
        if max_duration and max_duration < duration:
            max_frames = int(max_duration * fps)
        else:
            max_frames = total_frames
        
        # إعداد الكاتب
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        # إعادة تعيين
        self.tracker.reset()
        if self.activity_detector:
            self.activity_detector.reset_history()
        
        # بيانات الأشخاص
        persons_data = {}
        person_snapshots = {}
        activity_stats = defaultdict(int)
        recognized_persons = set()
        
        snapshots_dir = Path(output_path).parent / "snapshots"
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        
        frame_count = 0
        processed_count = 0
        last_tracks = {}
        
        try:
            while frame_count < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                
                # معالجة كل N إطار
                if frame_count % self.frame_skip == 0:
                    processed_count += 1
                    
                    # 1. تتبع الأشخاص
                    tracks = self.tracker.track(frame)
                    last_tracks = tracks
                    
                    # 2. معالجة كل شخص
                    for tid, data in tracks.items():
                        x1, y1, x2, y2 = data['box']
                        
                        # تهيئة بيانات الشخص
                        if tid not in persons_data:
                            persons_data[tid] = {
                                'name': 'Unknown',
                                'activities': defaultdict(int),
                                'first_seen': frame_count,
                                'detection_count': 0
                            }
                        
                        pd = persons_data[tid]
                        pd['last_seen'] = frame_count
                        pd['detection_count'] += 1
                        pd['last_box'] = (x1, y1, x2, y2)
                        
                        # 3. التعرف على الوجوه (كل 10 إطارات)
                        if self.face_system and self.face_system.initialized:
                            if pd['name'] == 'Unknown' and processed_count % 10 == 0:
                                x1c, y1c = max(0, x1), max(0, y1)
                                x2c, y2c = min(width, x2), min(height, y2)
                                person_crop = frame[y1c:y2c, x1c:x2c]
                                
                                if person_crop.size > 0:
                                    faces = self.face_system.detect_faces(person_crop)
                                    if faces:
                                        best_face = max(faces, key=lambda f: f['det_score'])
                                        result = self.face_system.recognize_face(best_face['embedding'])
                                        if result:
                                            pd['name'] = result[0]
                                            pd['face_similarity'] = result[1]
                                            recognized_persons.add(result[0])
                                            logger.info(f"✓ تم التعرف على: {result[0]} ({result[1]:.1%})")
                        
                        # 4. كشف النشاط
                        activity = 'unknown'
                        activity_conf = 0.0
                        if self.activity_detector and self.activity_detector.initialized:
                            activity, activity_conf = self.activity_detector.detect_activity(
                                frame, (x1, y1, x2, y2), tid
                            )
                        else:
                            # Fallback بسيط
                            aspect = (x2 - x1) / max(1, y2 - y1)
                            if aspect > 1.5:
                                activity = 'sleeping'
                            elif aspect < 0.6:
                                activity = 'working'
                            else:
                                activity = 'idle'
                            activity_conf = 0.5
                        
                        pd['current_activity'] = activity
                        pd['activities'][activity] += 1
                        activity_stats[activity] += 1
                        
                        # 5. حفظ snapshot
                        if tid not in person_snapshots:
                            x1c, y1c = max(0, x1), max(0, y1)
                            x2c, y2c = min(width, x2), min(height, y2)
                            crop = frame[y1c:y2c, x1c:x2c]
                            if crop.size > 0:
                                snapshot_path = snapshots_dir / f"person_{tid}_{int(time.time())}.jpg"
                                cv2.imwrite(str(snapshot_path), crop)
                                person_snapshots[tid] = str(snapshot_path)
                else:
                    tracks = last_tracks
                
                # رسم المعلومات
                for tid, data in tracks.items():
                    x1, y1, x2, y2 = data['box']
                    color = self.colors[tid % len(self.colors)]
                    
                    # المستطيل
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    
                    # المعلومات
                    pd = persons_data.get(tid, {})
                    name = pd.get('name', 'Unknown')
                    activity = pd.get('current_activity', 'unknown')
                    
                    if self.activity_detector:
                        activity_ar = self.activity_detector.get_activity_arabic(activity)
                    else:
                        activity_ar = activity
                    
                    label = f"{name} | {activity_ar}"
                    self._draw_label(frame, label, x1, y1 - 10, color)
                
                # العداد
                unique = self.tracker.get_unique_persons_count()
                current = len(tracks)
                recognized = len(recognized_persons)
                self._draw_stats(frame, unique, current, recognized)
                
                out.write(frame)
                
                # تقرير
                if processed_count % 50 == 0:
                    progress = (frame_count / max_frames) * 100
                    logger.info(f"⏳ {progress:.1f}% | فريدين: {unique} | معروفين: {recognized}")
        
        finally:
            cap.release()
            out.release()
        
        # النتائج
        processing_time = time.time() - start_time
        unique_persons = self.tracker.get_unique_persons_count()
        
        # تجميع الأنشطة
        activities_summary = []
        for tid, pd in persons_data.items():
            main_activity = max(pd['activities'].items(), key=lambda x: x[1])[0] if pd['activities'] else 'unknown'
            activities_summary.append({
                'person_id': tid,
                'name': pd.get('name', 'Unknown'),
                'main_activity': main_activity,
                'detection_count': pd.get('detection_count', 0),
                'snapshot': person_snapshots.get(tid)
            })
        
        results = {
            'success': True,
            'total_frames': frame_count,
            'processed_frames': processed_count,
            'processing_time': round(processing_time, 2),
            'fps_achieved': round(processed_count / processing_time, 1) if processing_time > 0 else 0,
            'total_persons': unique_persons,
            'recognized_persons': len(recognized_persons),
            'recognized_names': list(recognized_persons),
            'activities': dict(activity_stats),
            'persons': activities_summary,
            'video_info': {
                'width': width,
                'height': height,
                'fps': fps,
                'duration': round(duration, 1)
            }
        }
        
        logger.info(f"✅ اكتملت المعالجة في {processing_time:.1f}s")
        logger.info(f"   - أشخاص: {unique_persons} | معروفين: {len(recognized_persons)}")
        logger.info(f"   - الأنشطة: {dict(activity_stats)}")
        
        return results
    
    def _draw_label(self, frame, text, x, y, color):
        """رسم نص مع خلفية"""
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.5
        thickness = 1
        
        (tw, th), _ = cv2.getTextSize(text, font, scale, thickness)
        y = max(th + 5, y)
        
        cv2.rectangle(frame, (x, y - th - 5), (x + tw + 5, y), color, -1)
        cv2.putText(frame, text, (x + 2, y - 3), font, scale, (255, 255, 255), thickness)
    
    def _draw_stats(self, frame, unique, current, recognized):
        """رسم الإحصائيات"""
        cv2.rectangle(frame, (10, 10), (200, 90), (0, 0, 0), -1)
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(frame, f"Total: {unique}", (15, 30), font, 0.6, (0, 255, 0), 2)
        cv2.putText(frame, f"Current: {current}", (15, 55), font, 0.6, (255, 255, 0), 2)
        cv2.putText(frame, f"Known: {recognized}", (15, 80), font, 0.6, (0, 200, 255), 2)
