"""
Enhanced Video Processor - Uses BoT-SORT tracking for accurate person counting
Phase 2 Implementation
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Optional
import time
import logging

from .tracker import PersonTracker

logger = logging.getLogger(__name__)


class EnhancedVideoProcessor:
    """معالج فيديو محسن مع تتبع BoT-SORT"""
    
    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        conf_threshold: float = 0.5,
        tracker_type: str = "botsort",
        frame_skip: int = 1
    ):
        """
        تهيئة المعالج
        
        Args:
            model_path: مسار نموذج YOLO
            conf_threshold: عتبة الثقة
            tracker_type: نوع المتتبع (botsort أو bytetrack)
            frame_skip: عدد الإطارات للتخطي
        """
        self.tracker = PersonTracker(model_path, conf_threshold, tracker_type)
        self.frame_skip = max(1, frame_skip)
        
        # ألوان للرسم
        self.colors = [
            (0, 255, 0),    # أخضر
            (255, 0, 0),    # أزرق
            (0, 0, 255),    # أحمر
            (255, 255, 0),  # سماوي
            (255, 0, 255),  # بنفسجي
            (0, 255, 255),  # أصفر
            (128, 255, 0),  # ليموني
            (255, 128, 0),  # برتقالي
        ]
        
        logger.info(f"✓ تم تهيئة المعالج المحسن (tracker={tracker_type}, frame_skip={frame_skip})")
    
    def process_video(
        self,
        input_path: str,
        output_path: str,
        max_duration: Optional[int] = None
    ) -> Dict:
        """
        معالجة فيديو مع تتبع دقيق
        
        Args:
            input_path: مسار الفيديو المدخل
            output_path: مسار الفيديو الناتج
            max_duration: الحد الأقصى للمدة (ثواني)
            
        Returns:
            نتائج المعالجة
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
        
        # حساب الإطارات للمعالجة
        if max_duration and max_duration < duration:
            max_frames = int(max_duration * fps)
        else:
            max_frames = total_frames
        
        # إعداد الكاتب
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        # إعادة تعيين المتتبع
        self.tracker.reset()
        
        # الإحصائيات
        frame_count = 0
        processed_count = 0
        last_tracks = {}
        
        # قائمة لتخزين لقطات الأشخاص
        person_snapshots = {}
        snapshots_dir = Path(output_path).parent / "snapshots"
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            while frame_count < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                
                # تتبع في كل إطار أو الإطارات المحددة
                if frame_count % self.frame_skip == 0:
                    processed_count += 1
                    tracks = self.tracker.track(frame)
                    last_tracks = tracks
                    
                    # حفظ لقطات للأشخاص الجدد
                    for tid, data in tracks.items():
                        if tid not in person_snapshots:
                            x1, y1, x2, y2 = data['box']
                            # التأكد من الحدود
                            x1, y1 = max(0, x1), max(0, y1)
                            x2, y2 = min(width, x2), min(height, y2)
                            
                            if x2 > x1 and y2 > y1:
                                crop = frame[y1:y2, x1:x2]
                                if crop.size > 0:
                                    snapshot_path = snapshots_dir / f"person_{tid}_{int(time.time())}.jpg"
                                    cv2.imwrite(str(snapshot_path), crop)
                                    person_snapshots[tid] = str(snapshot_path)
                else:
                    tracks = last_tracks
                
                # رسم المستطيلات والمعلومات
                for tid, data in tracks.items():
                    x1, y1, x2, y2 = data['box']
                    conf = data['conf']
                    
                    # لون فريد لكل شخص
                    color = self.colors[tid % len(self.colors)]
                    
                    # المستطيل
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    
                    # النص
                    label = f"ID:{tid} ({conf:.0%})"
                    self._draw_label(frame, label, x1, y1 - 10, color)
                
                # عداد الأشخاص
                unique_count = self.tracker.get_unique_persons_count()
                current_count = len(tracks)
                self._draw_counter(frame, unique_count, current_count)
                
                out.write(frame)
                
                # تقرير التقدم
                if processed_count % 50 == 0:
                    progress = (frame_count / max_frames) * 100
                    logger.info(f"⏳ التقدم: {progress:.1f}% | أشخاص فريدين: {unique_count}")
        
        finally:
            cap.release()
            out.release()
        
        # النتائج
        processing_time = time.time() - start_time
        unique_persons = self.tracker.get_unique_persons_count()
        
        results = {
            'success': True,
            'input_path': input_path,
            'output_path': output_path,
            'total_frames': frame_count,
            'processed_frames': processed_count,
            'processing_time': round(processing_time, 2),
            'fps_achieved': round(processed_count / processing_time, 1) if processing_time > 0 else 0,
            'total_persons': unique_persons,
            'person_snapshots': person_snapshots,
            'video_info': {
                'width': width,
                'height': height,
                'fps': fps,
                'duration': round(duration, 1)
            }
        }
        
        logger.info(f"✅ تمت المعالجة في {processing_time:.1f}s")
        logger.info(f"   - أشخاص فريدين: {unique_persons}")
        logger.info(f"   - إطارات معالجة: {processed_count}")
        
        return results
    
    def _draw_label(self, frame: np.ndarray, text: str, x: int, y: int, color: tuple):
        """رسم نص مع خلفية"""
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 2
        
        (text_width, text_height), baseline = cv2.getTextSize(
            text, font, font_scale, thickness
        )
        
        # تأكيد الحدود
        y = max(text_height + 5, y)
        
        cv2.rectangle(
            frame,
            (x, y - text_height - 5),
            (x + text_width + 5, y),
            color,
            -1
        )
        
        cv2.putText(
            frame, text,
            (x + 2, y - 3),
            font, font_scale,
            (255, 255, 255), thickness
        )
    
    def _draw_counter(self, frame: np.ndarray, unique_count: int, current_count: int):
        """رسم عداد الأشخاص"""
        text1 = f"Total: {unique_count}"
        text2 = f"Current: {current_count}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.8
        thickness = 2
        
        # خلفية
        cv2.rectangle(frame, (10, 10), (180, 70), (0, 0, 0), -1)
        
        # النصوص
        cv2.putText(frame, text1, (15, 35), font, font_scale, (0, 255, 0), thickness)
        cv2.putText(frame, text2, (15, 60), font, font_scale, (255, 255, 0), thickness)
