"""
قاعدة موحدة لمعالجات الفيديو (Base Video Processor)

يوفر واجهة موحدة وإدارة مشتركة للموارد لجميع معالجات الفيديو:
- SimpleVideoProcessor
- FastVideoProcessor
- Level2VideoProcessor
- EnhancedVideoProcessor
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """نتيجة معالجة الفيديو"""
    success: bool
    total_persons: int = 0
    known_persons: int = 0
    total_activities: int = 0
    activity_breakdown: Dict[str, float] = field(default_factory=dict)
    processing_time: float = 0.0
    total_frames: int = 0
    processed_frames: int = 0
    statistics: List[Dict[str, Any]] = field(default_factory=list)
    output_video: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل إلى قاموس"""
        return {
            'success': self.success,
            'total_persons': self.total_persons,
            'known_persons': self.known_persons,
            'total_activities': self.total_activities,
            'activity_breakdown': self.activity_breakdown,
            'processing_time': self.processing_time,
            'total_frames': self.total_frames,
            'processed_frames': self.processed_frames,
            'statistics': self.statistics,
            'output_video': self.output_video,
            'error': self.error
        }


@dataclass
class VideoInfo:
    """معلومات الفيديو"""
    width: int
    height: int
    fps: float
    total_frames: int
    duration: float
    
    @classmethod
    def from_capture(cls, cap: cv2.VideoCapture) -> 'VideoInfo':
        """إنشاء من VideoCapture"""
        return cls(
            width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            fps=cap.get(cv2.CAP_PROP_FPS) or 25.0,
            total_frames=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            duration=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / (cap.get(cv2.CAP_PROP_FPS) or 25.0)
        )


class BaseVideoProcessor(ABC):
    """
    قاعدة موحدة لمعالجات الفيديو
    
    المميزات:
    - واجهة موحدة لجميع المعالجات
    - إدارة مشتركة للموارد
    - تتبع التقدم
    - معالجة الأخطاء
    """
    
    def __init__(
        self,
        device: str = "cpu",
        imgsz: int = 640,
        conf_threshold: float = 0.35,
        enable_face_recognition: bool = True,
        enable_activity_recognition: bool = True,
        **kwargs
    ):
        """
        Args:
            device: "cpu" أو "cuda"
            imgsz: حجم الصورة للنموذج
            conf_threshold: عتبة الثقة
            enable_face_recognition: تفعيل التعرف على الوجوه
            enable_activity_recognition: تفعيل تحليل الأنشطة
        """
        self.device = device
        self.imgsz = imgsz
        self.conf_threshold = conf_threshold
        self.enable_face = enable_face_recognition
        self.enable_activity = enable_activity_recognition
        
        # مكونات مشتركة (يتم تهيئتها في الفئات الفرعية)
        self.person_detector = None
        self.tracker = None
        self.face_recognizer = None
        self.activity_detector = None
        
        # إحصائيات
        self._stats = {
            'frames_processed': 0,
            'persons_detected': 0,
            'faces_recognized': 0,
            'activities_detected': 0,
            'processing_start': None,
            'processing_end': None
        }
        
        logger.info(f"تهيئة {self.__class__.__name__}")
        logger.info(f"  - Device: {device}")
        logger.info(f"  - Image size: {imgsz}")
        logger.info(f"  - Confidence: {conf_threshold}")
    
    @abstractmethod
    def _init_components(self):
        """تهيئة المكونات (يجب تنفيذها في الفئات الفرعية)"""
        pass
    
    @abstractmethod
    def process_frame(
        self,
        frame: np.ndarray,
        frame_num: int,
        frame_time: float
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """
        معالجة إطار واحد
        
        Args:
            frame: الإطار
            frame_num: رقم الإطار
            frame_time: وقت الإطار بالثواني
            
        Returns:
            (processed_frame, detections)
        """
        pass
    
    def process_video(
        self,
        input_path: str,
        output_path: str,
        frame_skip: int = 2,
        max_duration: int = -1,
        task_id: Optional[str] = None,
        enable_progress_tracking: bool = True
    ) -> ProcessingResult:
        """
        معالجة فيديو كامل
        
        Args:
            input_path: مسار الفيديو المدخل
            output_path: مسار الفيديو الناتج
            frame_skip: عدد الإطارات للتخطي
            max_duration: المدة القصوى بالثواني (-1 = كامل)
            task_id: معرف المهمة للتتبع
            enable_progress_tracking: تفعيل تتبع التقدم
            
        Returns:
            ProcessingResult
        """
        self._stats['processing_start'] = time.time()
        
        # فتح الفيديو
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            return ProcessingResult(success=False, error="فشل فتح الفيديو")
        
        try:
            video_info = VideoInfo.from_capture(cap)
            logger.info(f"📹 الفيديو: {video_info.width}x{video_info.height}, {video_info.fps:.1f}fps")
            
            # حساب الحد الأقصى للإطارات
            if max_duration > 0:
                max_frames = int(max_duration * video_info.fps)
            else:
                max_frames = video_info.total_frames
            
            # إعداد الفيديو الناتج
            output_file = self._prepare_output_video(output_path, video_info)
            
            # بيانات المعالجة
            all_detections = []
            person_data = {}
            frame_num = 0
            processed_frames = 0
            
            while cap.isOpened() and frame_num < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_num += 1
                
                # تخطي الإطارات
                if frame_skip > 0 and frame_num % (frame_skip + 1) != 0:
                    continue
                
                current_time = frame_num / video_info.fps
                processed_frames += 1
                
                # معالجة الإطار
                processed_frame, detections = self.process_frame(
                    frame, frame_num, current_time
                )
                
                # تجميع البيانات
                self._aggregate_detections(detections, person_data, current_time)
                all_detections.extend(detections)
                
                # كتابة الإطار
                if output_file:
                    output_file.write(processed_frame)
                
                # تقدم كل 50 إطار
                if frame_num % 50 == 0:
                    progress = 100 * frame_num / max_frames
                    logger.info(f"⏳ معالجة: {frame_num}/{max_frames} ({progress:.1f}%)")
            
        finally:
            cap.release()
            if output_file:
                output_file.release()
        
        self._stats['processing_end'] = time.time()
        processing_time = self._stats['processing_end'] - self._stats['processing_start']
        
        logger.info(f"✅ انتهت المعالجة: {frame_num} إطار في {processing_time:.2f}s")
        
        # حساب النتائج
        return self._calculate_results(
            person_data, 
            video_info.fps, 
            processing_time, 
            processed_frames,
            output_path
        )
    
    def _prepare_output_video(
        self, 
        output_path: str, 
        video_info: VideoInfo
    ) -> Optional[cv2.VideoWriter]:
        """إعداد ملف الفيديو الناتج"""
        try:
            output_file = output_path.replace('.mp4', '.avi')
            return cv2.VideoWriter(
                output_file,
                cv2.VideoWriter_fourcc(*'XVID'),
                video_info.fps,
                (video_info.width, video_info.height)
            )
        except Exception as e:
            logger.warning(f"فشل إعداد الفيديو الناتج: {e}")
            return None
    
    def _aggregate_detections(
        self,
        detections: List[Dict[str, Any]],
        person_data: Dict[int, Dict],
        current_time: float
    ):
        """تجميع الكشوفات"""
        for det in detections:
            track_id = det.get('track_id', 0)
            
            if track_id not in person_data:
                person_data[track_id] = {
                    'activities': [],
                    'first_time': current_time,
                    'last_time': current_time,
                    'name': det.get('name', 'Unknown'),
                    'snapshot': None
                }
            
            person_data[track_id]['last_time'] = current_time
            
            activity = det.get('activity', 'unknown')
            if activity:
                person_data[track_id]['activities'].append((current_time, activity))
    
    def _calculate_results(
        self,
        person_data: Dict,
        fps: float,
        processing_time: float,
        processed_frames: int,
        output_path: str
    ) -> ProcessingResult:
        """حساب النتائج النهائية"""
        statistics = []
        activity_counts = {}
        
        for track_id, data in person_data.items():
            # حساب مدة كل نشاط
            activity_durations = {}
            for time_val, activity in data['activities']:
                if activity != 'unknown':
                    if activity not in activity_durations:
                        activity_durations[activity] = 0
                    activity_durations[activity] += 1 / fps
            
            # إحصائيات الشخص
            total_duration = len(data['activities']) / fps if data['activities'] else 0.0
            top_activity = max(activity_durations.keys(), key=lambda k: activity_durations[k]) if activity_durations else 'unknown'
            
            statistics.append({
                'name': data['name'],
                'track_id': track_id,
                'count': len(data['activities']),
                'top_activity': top_activity,
                'duration': total_duration,
                'working_duration': activity_durations.get('working', 0.0),
                'sleeping_duration': activity_durations.get('sleeping', 0.0),
                'phone_duration': activity_durations.get('on_phone', 0.0),
            })
            
            # تجميع الأنشطة الكلية
            for activity, duration in activity_durations.items():
                activity_counts[activity] = activity_counts.get(activity, 0) + duration
        
        return ProcessingResult(
            success=True,
            total_persons=len(person_data),
            known_persons=sum(1 for s in statistics if s['name'] != 'Unknown'),
            total_activities=sum(activity_counts.values()),
            activity_breakdown=activity_counts,
            processing_time=processing_time,
            total_frames=processed_frames,
            processed_frames=processed_frames,
            statistics=statistics,
            output_video=output_path.replace('.mp4', '.avi')
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """الحصول على إحصائيات المعالجة"""
        return self._stats.copy()
    
    def reset_stats(self):
        """إعادة تعيين الإحصائيات"""
        self._stats = {
            'frames_processed': 0,
            'persons_detected': 0,
            'faces_recognized': 0,
            'activities_detected': 0,
            'processing_start': None,
            'processing_end': None
        }
