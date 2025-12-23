"""
Simple Video Processor - Basic video processing with person detection
Fresh start implementation - Phase 1
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Optional
import time
import logging

from .detector import PersonDetector

logger = logging.getLogger(__name__)


class SimpleVideoProcessor:
    """معالج فيديو بسيط مع كشف الأشخاص"""
    
    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        conf_threshold: float = 0.5,
        frame_skip: int = 1
    ):
        """
        تهيئة المعالج
        
        Args:
            model_path: مسار نموذج YOLO
            conf_threshold: عتبة الثقة
            frame_skip: عدد الإطارات للتخطي (1 = معالجة كل إطار)
        """
        self.detector = PersonDetector(model_path, conf_threshold)
        self.frame_skip = max(1, frame_skip)
        
        # ألوان للرسم
        self.box_color = (0, 255, 0)  # أخضر
        self.text_color = (255, 255, 255)  # أبيض
        self.text_bg_color = (0, 100, 0)  # أخضر داكن
        
        logger.info(f"✓ تم تهيئة معالج الفيديو البسيط (frame_skip={frame_skip})")
    
    def process_video(
        self,
        input_path: str,
        output_path: str,
        max_duration: Optional[int] = None
    ) -> Dict:
        """
        معالجة فيديو وحفظ الناتج
        
        Args:
            input_path: مسار الفيديو المدخل
            output_path: مسار الفيديو الناتج
            max_duration: الحد الأقصى للمدة بالثواني (None = كامل الفيديو)
            
        Returns:
            إحصائيات المعالجة
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
        
        # الإحصائيات
        frame_count = 0
        processed_count = 0
        total_detections = 0
        max_persons_in_frame = 0
        
        try:
            while frame_count < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                
                # تخطي الإطارات
                if frame_count % self.frame_skip != 0:
                    out.write(frame)
                    continue
                
                processed_count += 1
                
                # كشف الأشخاص
                count, detections = self.detector.detect_count(frame)
                total_detections += count
                max_persons_in_frame = max(max_persons_in_frame, count)
                
                # رسم المستطيلات
                for det in detections:
                    x1, y1, x2, y2 = det['box']
                    conf = det['confidence']
                    
                    # المستطيل
                    cv2.rectangle(frame, (x1, y1), (x2, y2), self.box_color, 2)
                    
                    # النص
                    label = f"Person {conf:.1%}"
                    self._draw_label(frame, label, x1, y1 - 10)
                
                # عداد الأشخاص في الزاوية
                self._draw_counter(frame, count)
                
                out.write(frame)
                
                # تقرير التقدم
                if processed_count % 100 == 0:
                    progress = (frame_count / max_frames) * 100
                    logger.info(f"⏳ التقدم: {progress:.1f}%")
        
        finally:
            cap.release()
            out.release()
        
        # النتائج
        processing_time = time.time() - start_time
        avg_persons = total_detections / processed_count if processed_count > 0 else 0
        
        results = {
            'success': True,
            'input_path': input_path,
            'output_path': output_path,
            'total_frames': frame_count,
            'processed_frames': processed_count,
            'processing_time': processing_time,
            'fps_achieved': processed_count / processing_time if processing_time > 0 else 0,
            'total_detections': total_detections,
            'max_persons_in_frame': max_persons_in_frame,
            'avg_persons_per_frame': avg_persons,
            'video_info': {
                'width': width,
                'height': height,
                'fps': fps,
                'duration': duration
            }
        }
        
        logger.info(f"✅ تمت المعالجة في {processing_time:.1f}s")
        logger.info(f"   - إطارات معالجة: {processed_count}")
        logger.info(f"   - أقصى عدد أشخاص: {max_persons_in_frame}")
        logger.info(f"   - متوسط الأشخاص: {avg_persons:.1f}")
        
        return results
    
    def _draw_label(self, frame: np.ndarray, text: str, x: int, y: int):
        """رسم نص مع خلفية"""
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1
        
        (text_width, text_height), baseline = cv2.getTextSize(
            text, font, font_scale, thickness
        )
        
        cv2.rectangle(
            frame,
            (x, y - text_height - 5),
            (x + text_width + 5, y),
            self.text_bg_color,
            -1
        )
        
        cv2.putText(
            frame, text,
            (x + 2, y - 3),
            font, font_scale,
            self.text_color, thickness
        )
    
    def _draw_counter(self, frame: np.ndarray, count: int):
        """رسم عداد الأشخاص في الزاوية"""
        text = f"Persons: {count}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.0
        thickness = 2
        
        (text_width, text_height), _ = cv2.getTextSize(
            text, font, font_scale, thickness
        )
        
        # خلفية
        cv2.rectangle(
            frame,
            (10, 10),
            (20 + text_width, 25 + text_height),
            (0, 0, 0),
            -1
        )
        
        # النص
        cv2.putText(
            frame, text,
            (15, 20 + text_height),
            font, font_scale,
            (0, 255, 0), thickness
        )
