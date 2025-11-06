"""
TimeTracker: تتبّع مقاطع الأنشطة بدقة زمنية عالية لكل track (موظف/مسار تتبّع).
- لا يخزّن الفريمات؛ فقط الأحداث/المقاطع لتوفير الذاكرة.
- يدعم حدًا أدنى لمدة المقطع لتصفية التذبذبات السريعة.
"""
from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


@dataclass
class ActivitySegment:
    activity: str
    start_time: datetime
    end_time: Optional[datetime]
    duration: float  # seconds
    camera_id: str


@dataclass
class TrackState:
    employee_id: str
    current_activity: Optional[str] = None
    activity_start_time: Optional[datetime] = None
    camera_id: str = ""
    segments: List[ActivitySegment] = field(default_factory=list)


class TimeTracker:
    """مدير تتبّع الوقت للمقاطع حسب track_id.

    المعاملات:
    - min_segment_duration: الحد الأدنى لمدة المقطع بالثواني لقبوله عند الإغلاق.
    """

    def __init__(self, min_segment_duration: float = 5.0) -> None:
        self.min_segment_duration = float(min_segment_duration)
        self.tracks: Dict[str, TrackState] = {}

    # --------------------------- عمليات أساسية ---------------------------
    def start_activity(self, track_id: str, employee_id: str, activity: str, timestamp: datetime, camera_id: str) -> None:
        """بدء تتبّع نشاط لمسار محدد. إذا كان هناك نشاط جارٍ، سيتم إغلاقه أولاً."""
        st = self.tracks.get(track_id)
        if st is None:
            st = TrackState(employee_id=employee_id, current_activity=None, activity_start_time=None, camera_id=camera_id)
            self.tracks[track_id] = st
        else:
            # في حال اختلاف الموظف لنفس track (نادر)، نغلق ونعيد التهيئة
            if st.employee_id != employee_id:
                logger.warning("تغيير employee_id لمسار %s من %s إلى %s", track_id, st.employee_id, employee_id)
                self.end_tracking(track_id, timestamp)
                st = TrackState(employee_id=employee_id, current_activity=None, activity_start_time=None, camera_id=camera_id)
                self.tracks[track_id] = st
        # إذا كان هناك نشاط جارٍ مختلف، أغلقه
        if st.current_activity is not None and st.activity_start_time is not None:
            if st.current_activity != activity:
                self._close_segment(track_id, timestamp)
        # ابدأ/حدّث النشاط الحالي
        st.current_activity = activity
        st.activity_start_time = timestamp
        st.camera_id = camera_id

    def update_activity(self, track_id: str, new_activity: str, timestamp: datetime) -> None:
        """تحديث نشاط المسار. إذا تغيّر النشاط، أغلق المقطع السابق وابدأ جديداً."""
        st = self.tracks.get(track_id)
        if st is None:
            logger.debug("update_activity: لا توجد حالة للمسار %s، سيتم البدء تلقائياً", track_id)
            return
        if st.current_activity is None or st.activity_start_time is None:
            st.current_activity = new_activity
            st.activity_start_time = timestamp
            return
        if new_activity != st.current_activity:
            self._close_segment(track_id, timestamp)
            # ابدأ مقطعاً جديداً
            st.current_activity = new_activity
            st.activity_start_time = timestamp

    def end_tracking(self, track_id: str, timestamp: datetime) -> None:
        """إنهاء تتبّع المسار وإغلاق أي مقطع جارٍ."""
        st = self.tracks.get(track_id)
        if st is None:
            return
        if st.current_activity is not None and st.activity_start_time is not None:
            self._close_segment(track_id, timestamp)
        # لا نحذف السجل حتى يمكن استعراضه لاحقاً

    # --------------------------- أدوات داخلية ---------------------------
    def _close_segment(self, track_id: str, end_time: datetime) -> None:
        st = self.tracks.get(track_id)
        if st is None or st.current_activity is None or st.activity_start_time is None:
            return
        duration = max(0.0, (end_time - st.activity_start_time).total_seconds())
        if duration < self.min_segment_duration:
            # تجاهل المقاطع القصيرة جداً لتجنّب التذبذب
            logger.debug("تجاهل مقطع قصير: track=%s act=%s dur=%.3fs < %.3fs", track_id, st.current_activity, duration, self.min_segment_duration)
        else:
            seg = ActivitySegment(
                activity=st.current_activity,
                start_time=st.activity_start_time,
                end_time=end_time,
                duration=duration,
                camera_id=st.camera_id,
            )
            st.segments.append(seg)
        # مسح النشاط الحالي
        st.current_activity = None
        st.activity_start_time = None

    # --------------------------- استعلامات/تقارير ---------------------------
    def get_activity_summary(self, track_id: str) -> Dict[str, float]:
        """ملخّص الوقت بالثواني لكل نشاط بالإضافة إلى الإجمالي."""
        st = self.tracks.get(track_id)
        summary: Dict[str, float] = {"total": 0.0}
        if st is None:
            return summary
        for seg in st.segments:
            summary[seg.activity] = summary.get(seg.activity, 0.0) + seg.duration
            summary["total"] += seg.duration
        return summary

    def get_segments(self, track_id: str) -> List[Dict[str, object]]:
        """إرجاع قائمة المقاطع كقواميس قابلة للتسلسل."""
        st = self.tracks.get(track_id)
        if st is None:
            return []
        res: List[Dict[str, object]] = []
        for seg in st.segments:
            res.append(
                {
                    "activity": seg.activity,
                    "start_time": seg.start_time.isoformat(),
                    "end_time": seg.end_time.isoformat() if seg.end_time else None,
                    "duration": seg.duration,
                    "camera_id": seg.camera_id,
                }
            )
        return res

    def export_segments(self, track_id: str, format: str = "csv") -> str:
        """تصدير المقاطع كسلسلة نصية. حالياً يدعم CSV."""
        if format.lower() != "csv":
            raise ValueError("تنسيق غير مدعوم حالياً، استخدم 'csv'")
        rows = self.get_segments(track_id)
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["activity", "start_time", "end_time", "duration", "camera_id"], extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
        return output.getvalue()
