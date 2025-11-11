# -*- coding: utf-8 -*-
"""
Progress Tracker - تتبع تقدم المعالجة
يوفر:
1. تتبع النسبة المئوية للإنجاز
2. تقدير الوقت المتبقي
3. معدل المعالجة (FPS)
4. إحصائيات التقدم
"""
from __future__ import annotations
import time
import threading
from typing import Dict, Optional
from dataclasses import dataclass
from collections import deque


@dataclass
class ProgressStats:
    """إحصائيات التقدم"""
    total_frames: int
    processed_frames: int
    progress_percent: float
    elapsed_time: float
    estimated_remaining_time: float
    processing_fps: float
    current_status: str


class ProgressTracker:
    """تتبع تقدم المعالجة"""
    
    def __init__(self, total_frames: int, task_id: str = "default"):
        """
        Args:
            total_frames: إجمالي عدد الإطارات
            task_id: معرف المهمة
        """
        self.total_frames = total_frames
        self.task_id = task_id
        self.processed_frames = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.current_status = "جاري التحضير..."
        
        # تتبع FPS (آخر 30 إطار)
        self.frame_times = deque(maxlen=30)
        self.lock = threading.Lock()
    
    def update(self, frames_processed: int = 1, status: Optional[str] = None):
        """
        تحديث التقدم
        
        Args:
            frames_processed: عدد الإطارات المعالجة
            status: الحالة الحالية (اختياري)
        """
        with self.lock:
            current_time = time.time()
            
            # تحديث عدد الإطارات
            self.processed_frames += frames_processed
            
            # تحديث الحالة
            if status:
                self.current_status = status
            
            # حساب الوقت لكل إطار
            time_delta = current_time - self.last_update_time
            if time_delta > 0:
                self.frame_times.append(time_delta / frames_processed)
            
            self.last_update_time = current_time
    
    def get_stats(self) -> ProgressStats:
        """الحصول على إحصائيات التقدم"""
        with self.lock:
            current_time = time.time()
            elapsed_time = current_time - self.start_time
            
            # النسبة المئوية
            progress_percent = (self.processed_frames / self.total_frames * 100) if self.total_frames > 0 else 0
            
            # FPS الحالي
            if self.frame_times:
                avg_frame_time = sum(self.frame_times) / len(self.frame_times)
                processing_fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
            else:
                processing_fps = 0
            
            # تقدير الوقت المتبقي
            remaining_frames = self.total_frames - self.processed_frames
            if processing_fps > 0:
                estimated_remaining_time = remaining_frames / processing_fps
            else:
                estimated_remaining_time = 0
            
            return ProgressStats(
                total_frames=self.total_frames,
                processed_frames=self.processed_frames,
                progress_percent=min(progress_percent, 100.0),
                elapsed_time=elapsed_time,
                estimated_remaining_time=estimated_remaining_time,
                processing_fps=processing_fps,
                current_status=self.current_status
            )
    
    def get_progress_dict(self) -> Dict:
        """الحصول على التقدم كـ dictionary (للـ JSON)"""
        stats = self.get_stats()
        return {
            'task_id': self.task_id,
            'total_frames': stats.total_frames,
            'processed_frames': stats.processed_frames,
            'progress_percent': round(stats.progress_percent, 1),
            'elapsed_time': round(stats.elapsed_time, 1),
            'estimated_remaining_time': round(stats.estimated_remaining_time, 1),
            'processing_fps': round(stats.processing_fps, 1),
            'status': stats.current_status,
            'is_complete': stats.processed_frames >= stats.total_frames
        }
    
    def get_progress_message(self) -> str:
        """الحصول على رسالة التقدم (نص)"""
        stats = self.get_stats()
        
        mins_elapsed = int(stats.elapsed_time // 60)
        secs_elapsed = int(stats.elapsed_time % 60)
        
        mins_remaining = int(stats.estimated_remaining_time // 60)
        secs_remaining = int(stats.estimated_remaining_time % 60)
        
        return (
            f"[{stats.progress_percent:.0f}%] "
            f"{stats.processed_frames}/{stats.total_frames} إطار | "
            f"السرعة: {stats.processing_fps:.1f} FPS | "
            f"مضى: {mins_elapsed}:{secs_elapsed:02d} | "
            f"متبقي: {mins_remaining}:{secs_remaining:02d} | "
            f"{stats.current_status}"
        )
    
    def reset(self):
        """إعادة تعيين المتتبع"""
        with self.lock:
            self.processed_frames = 0
            self.start_time = time.time()
            self.last_update_time = self.start_time
            self.current_status = "جاري التحضير..."
            self.frame_times.clear()
    
    def is_complete(self) -> bool:
        """التحقق من اكتمال المعالجة"""
        return self.processed_frames >= self.total_frames


# Global progress tracker storage
_progress_trackers: Dict[str, ProgressTracker] = {}
_trackers_lock = threading.Lock()


def get_or_create_tracker(task_id: str, total_frames: int) -> ProgressTracker:
    """الحصول على أو إنشاء متتبع للمهمة"""
    with _trackers_lock:
        if task_id not in _progress_trackers:
            _progress_trackers[task_id] = ProgressTracker(total_frames, task_id)
        return _progress_trackers[task_id]


def get_tracker(task_id: str) -> Optional[ProgressTracker]:
    """الحصول على متتبع المهمة"""
    with _trackers_lock:
        return _progress_trackers.get(task_id)


def remove_tracker(task_id: str):
    """إزالة متتبع المهمة"""
    with _trackers_lock:
        if task_id in _progress_trackers:
            del _progress_trackers[task_id]


def get_all_progress() -> Dict[str, Dict]:
    """الحصول على تقدم جميع المهام"""
    with _trackers_lock:
        return {
            task_id: tracker.get_progress_dict()
            for task_id, tracker in _progress_trackers.items()
        }


# مثال الاستخدام
if __name__ == "__main__":
    import random
    
    # محاكاة معالجة فيديو
    tracker = ProgressTracker(total_frames=100, task_id="test_video")
    
    for i in range(100):
        # محاكاة معالجة إطار
        time.sleep(random.uniform(0.01, 0.05))
        
        # تحديث التقدم
        status = "جاري الكشف..." if i < 50 else "جاري التتبع..."
        tracker.update(frames_processed=1, status=status)
        
        # طباعة التقدم كل 10 إطارات
        if i % 10 == 0:
            print(tracker.get_progress_message())
    
    print("\n✓ اكتمل!")
    print(tracker.get_progress_dict())
