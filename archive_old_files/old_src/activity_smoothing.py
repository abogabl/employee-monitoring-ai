"""
ActivitySmoother: تنعيم زمني للأنشطة لتقليل التذبذب باستخدام نافذة زمنية وثقة.
- Majority voting على آخر N ثوانٍ.
- تجاهل التغييرات القصيرة جداً عبر حد أدنى للمدة.
"""
from __future__ import annotations

import logging
from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Deque, List, Optional, Tuple

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


@dataclass
class Detection:
    activity: str
    timestamp: datetime
    confidence: float


class ActivitySmoother:
    """تنعيم زمني بسيط قائم على نافذة ثوانٍ وتعددية الأصوات."""

    def __init__(self, window_size: float = 5.0, min_change_duration: float = 2.0) -> None:
        self.window_size = float(window_size)
        self.min_change_duration = float(min_change_duration)
        self.buffer: Deque[Detection] = deque()
        self._last_output: Optional[Detection] = None

    def add_detection(self, activity: str, timestamp: datetime, confidence: float) -> None:
        """إضافة كشف نشاط جديد مع طابع زمني وثقة."""
        det = Detection(activity=activity, timestamp=timestamp, confidence=float(confidence))
        self.buffer.append(det)
        # إزالة العناصر الأقدم من نافذة الوقت
        cutoff = timestamp - timedelta(seconds=self.window_size)
        while self.buffer and self.buffer[0].timestamp < cutoff:
            self.buffer.popleft()

    def get_smoothed_activity(self) -> Tuple[Optional[str], float]:
        """إرجاع النشاط المموّه (الأكثر تصويتاً) ومتوسط الثقة له."""
        if not self.buffer:
            return None, 0.0
        counts = Counter(d.activity for d in self.buffer)
        best_act, _ = counts.most_common(1)[0]
        confs = [d.confidence for d in self.buffer if d.activity == best_act]
        avg_conf = sum(confs) / max(1, len(confs))
        return best_act, float(avg_conf)

    def should_update(self) -> bool:
        """يُقرّر إن كان يجب إخراج تغيير نشاط جديد أم لا وفق مدة التغير الأدنى."""
        if not self.buffer:
            return False
        current_act, _ = self.get_smoothed_activity()
        if current_act is None:
            return False
        latest_time = self.buffer[-1].timestamp
        if self._last_output is None:
            # أول ناتج مقبول فوراً
            self._last_output = Detection(activity=current_act, timestamp=latest_time, confidence=1.0)
            return True
        if current_act != self._last_output.activity:
            # تغيّر مقترح: لا نعتمده إلا إذا استمر على الأقل min_change_duration
            # نحسب منذ أول ظهور للنشاط الحالي ضمن النافذة
            first_time = None
            for d in self.buffer:
                if d.activity == current_act:
                    first_time = d.timestamp
                    break
            if first_time is None:
                return False
            if (latest_time - first_time).total_seconds() >= self.min_change_duration:
                self._last_output = Detection(activity=current_act, timestamp=latest_time, confidence=1.0)
                return True
            return False
        else:
            # لم يتغير النشاط
            self._last_output.timestamp = latest_time
            return False
