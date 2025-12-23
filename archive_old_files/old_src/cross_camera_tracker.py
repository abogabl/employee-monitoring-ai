"""
CrossCameraTracker: تتبّع حركة الموظف بين الكاميرات وربط الظهور عبر الزمن.
- يحفظ آخر موقع لكل موظف وتاريخ الحركة بين الكاميرات.
- يكتشف حالات مريبة (ظهور متزامن في كاميرتين بعيدتين).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


@dataclass
class MovementRecord:
    employee_id: str
    from_camera: Optional[str]
    to_camera: str
    timestamp: datetime


class CrossCameraTracker:
    """متعقّب انتقال الموظف بين الكاميرات."""

    def __init__(self, suspicious_minutes: float = 1.5) -> None:
        self.current_location: Dict[str, str] = {}  # emp_id -> camera_id
        self.movement_history: Dict[str, List[MovementRecord]] = {}
        self.suspicious_window = timedelta(minutes=float(suspicious_minutes))

    def track_employee_movement(self, employee_id: str, cameras_data: Dict[str, dict]) -> None:
        """تحديث موقع الموظف لو تم رصده في كاميرا جديدة ضمن البيانات المدخلة.
        cameras_data: {camera_id: {"seen_employees": set([...]), "timestamp": datetime}}
        """
        for cam_id, info in cameras_data.items():
            seen = info.get("seen_employees", set())
            ts = info.get("timestamp")
            if employee_id in seen:
                prev = self.current_location.get(employee_id)
                if prev != cam_id:
                    self.current_location[employee_id] = cam_id
                    rec = MovementRecord(employee_id=employee_id, from_camera=prev, to_camera=cam_id, timestamp=ts)
                    self.movement_history.setdefault(employee_id, []).append(rec)
                    logger.info("تنقل الموظف %s من %s إلى %s @ %s", employee_id, prev, cam_id, ts)

    def get_employee_location(self, employee_id: str) -> Optional[str]:
        return self.current_location.get(employee_id)

    def get_movement_history(self, employee_id: str, d: Optional[str] = None) -> List[dict]:
        recs = self.movement_history.get(employee_id, [])
        if d:
            recs = [r for r in recs if r.timestamp.date().isoformat() == d]
        return [
            {"employee_id": r.employee_id, "from_camera": r.from_camera, "to_camera": r.to_camera, "timestamp": r.timestamp.isoformat()}
            for r in recs
        ]

    def detect_suspicious_movement(self) -> List[dict]:
        """حالات مريبة: انتقال بين كاميرتين بعيدتين في وقت قصير جداً.
        يحتاج خريطة مسافات حقيقية بين المواقع لتكون دقيقة؛ هنا معيار زمني فقط.
        """
        alerts: List[dict] = []
        for emp, recs in self.movement_history.items():
            recs_sorted = sorted(recs, key=lambda r: r.timestamp)
            for i in range(1, len(recs_sorted)):
                if (recs_sorted[i].timestamp - recs_sorted[i - 1].timestamp) <= self.suspicious_window:
                    alerts.append({
                        "employee_id": emp,
                        "from": recs_sorted[i - 1].to_camera,
                        "to": recs_sorted[i].to_camera,
                        "t1": recs_sorted[i - 1].timestamp.isoformat(),
                        "t2": recs_sorted[i].timestamp.isoformat(),
                        "issue": "سفر سريع بين الكاميرات"
                    })
        return alerts
