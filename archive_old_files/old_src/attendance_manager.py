"""
AttendanceManager: ربط التعرف على الوجوه والأنشطة مع نظام الحضور.
- يقرر check-in / update / check-out بناءً على النشاط والحضور الفعلي.
- يحسب إنتاجية تقريبية بالاعتماد على الزمن المقضي في الأنشطة "المنتجة".
- يكشف بعض الحالات غير الطبيعية.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .attendance_system import AttendanceSystem

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


PRODUCTIVE_ACTIVITIES = {"working", "meeting"}
BREAKLIKE_ACTIVITIES = {"idle", "on_phone"}


@dataclass
class PresenceState:
    employee_id: str
    employee_name: str
    camera_id: str
    last_activity: str = "idle"
    last_seen: Optional[datetime] = None


class AttendanceManager:
    """مدير الحضور المتكامل مع الأنشطة.

    الاستخدام:
    - استدعاء process_person_detection لكل كشف معرف لشخص مع نشاطه والزمن.
    - استدعاء handle_disappearance عند اختفاء الشخص لتطبيق فترة السماح ثم تسجيل الخروج.
    """

    def __init__(self, system: AttendanceSystem, grace_seconds: int = 60) -> None:
        self.system = system
        self.grace = int(grace_seconds)
        # حالة الحضور اللحظية
        self.presence: Dict[str, PresenceState] = {}
        # تجميع إنتاجية لكل يوم: emp_id -> date_str -> نشاط -> ثواني
        self.activity_seconds: Dict[str, Dict[str, Dict[str, float]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        # آخر طابع زمني مرصود لكل موظف لحساب الفواصل
        self.last_seen_ts: Dict[str, datetime] = {}

    # --------------------------- قرار التدفق ---------------------------
    def process_person_detection(
        self,
        employee_id: str,
        camera_id: str,
        activity: str,
        timestamp: datetime,
        employee_name: Optional[str] = None,
    ) -> None:
        """معالجة كشف شخص واحد: قد يؤدي لتسجيل دخول/تحديث/حساب إنتاجية."""
        emp_name = employee_name or employee_id
        ps = self.presence.get(employee_id)
        now = timestamp
        date_str = self.system._date_str(now)

        # تسجيل دخول إن لم يكن موجوداً مسبقاً
        if not self.system.is_employee_present(employee_id):
            ok = self.system.check_in(employee_id, camera_id, now, employee_name=emp_name)
            if ok:
                logger.info("[Attendance] Check-in %s via camera=%s", employee_id, camera_id)

        # تحديث حالة داخلية
        if ps is None:
            ps = PresenceState(employee_id=employee_id, employee_name=emp_name, camera_id=camera_id, last_activity=activity, last_seen=now)
            self.presence[employee_id] = ps
        else:
            # تراكم زمن النشاط السابق
            prev_ts = self.last_seen_ts.get(employee_id, now)
            dt = max(0.0, (now - prev_ts).total_seconds())
            self.activity_seconds[employee_id][date_str][ps.last_activity] += dt
            ps.last_activity = activity
            ps.last_seen = now

        self.last_seen_ts[employee_id] = now

        # تحديث حالة السجل المفتوح (اختياري: on_break للأنشطة الخاملة لفترات طويلة)
        if activity in BREAKLIKE_ACTIVITIES:
            self.system.update_status(employee_id, "on_break", now)
        else:
            self.system.update_status(employee_id, "checked_in", now)

    def handle_disappearance(self, employee_id: str, last_seen: datetime, grace_seconds: Optional[int] = None) -> bool:
        """عند اختفاء موظف، انتظر فترة سماح ثم سجّل خروجاً. يرجع True إذا تم تسجيل خروج."""
        gsec = int(self.grace if grace_seconds is None else grace_seconds)
        now = self.system._now_local()
        if (now - last_seen).total_seconds() < gsec:
            return False
        # سجل خروج
        ok = self.system.check_out(employee_id, camera_id=self.presence.get(employee_id, PresenceState(employee_id, "", "")).camera_id, timestamp=now)
        if ok:
            # امسح الحالة الداخلية وخزن آخر نشاط
            self.presence.pop(employee_id, None)
            self.last_seen_ts.pop(employee_id, None)
        return ok

    # --------------------------- إنتاجية وشذوذ ---------------------------
    def calculate_productivity_score(self, employee_id: str, d: Optional[str] = None) -> float:
        """حساب إنتاجية تقريبية كنسبة الزمن في الأنشطة المنتجة خلال اليوم."""
        if d is None:
            d = self.system._date_str(self.system._now_local())
        secs = self.activity_seconds.get(employee_id, {}).get(d, {})
        total = sum(secs.values())
        if total <= 0:
            # كبديل، استخدم ساعات العمل من الوجود في القاعدة
            hours = self.system.calculate_work_hours(employee_id, d)
            total = hours * 3600.0
            # لا توجد تفاصيل أنشطة: لا يمكن تقدير النسبة بدقة
            return 0.0 if total <= 0 else 0.5
        productive = sum(secs.get(a, 0.0) for a in PRODUCTIVE_ACTIVITIES)
        return float(max(0.0, min(1.0, productive / total)))

    def detect_anomalies(self, employee_id: str, d: Optional[str] = None) -> List[str]:
        """كشف بسيط للشذوذ: غياب طويل، إنتاجية منخفضة."""
        if d is None:
            d = self.system._date_str(self.system._now_local())
        issues: List[str] = []
        hours = self.system.calculate_work_hours(employee_id, d)
        if hours == 0:
            issues.append("غياب تام")
        elif hours < 4:
            issues.append("ساعات عمل أقل من 4 ساعات")
        score = self.calculate_productivity_score(employee_id, d)
        if score < 0.3:
            issues.append("إنتاجية منخفضة (<30%)")
        return issues
