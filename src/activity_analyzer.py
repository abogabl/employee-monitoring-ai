"""
ActivityAnalyzer: تحليلات يومية ومقارنات وأنماط ورؤى على بيانات الأنشطة.
يعتمد على سجلات TimeTracker أو ملخصات محسوبة من AttendanceManager.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .attendance_system import AttendanceSystem

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


PRODUCTIVE = {"working", "meeting"}
BREAKLIKE = {"idle"}
PHONE = {"on_phone"}


class ActivityAnalyzer:
    """محلل نشاطات فوق بيانات الحضور والمقاطع."""

    def __init__(self, attendance: Optional[AttendanceSystem] = None) -> None:
        self.attendance = attendance or AttendanceSystem()

    # ملاحظة: في هذا النموذج المرجعي، نفترض أن ملخصات الأنشطة لكل موظف/يوم تُحفظ أو تُحتسب خارجياً
    # يمكنك تمرير مصادر أخرى أو دمج TimeTracker لاحقاً.

    def analyze_employee_day(self, employee_id: str, d: date | str) -> Dict[str, object]:
        """تحليل يوم موظف: يعيد إجمالي ساعات العمل وتوزيع الأنشطة وتقدير الإنتاجية.
        حالياً يعتمد ساعات العمل من AttendanceSystem، ويمكن تمرير توزيع أنشطة خارجي لاحقاً.
        """
        d_str = d if isinstance(d, str) else d.isoformat()
        total_hours = float(self.attendance.calculate_work_hours(employee_id, d_str))
        # توزيع أنشطة تقريبي إن لم تتوفر بيانات دقيقة: نفترض 85% عمل و10% راحة و5% هاتف عند وجود حضور كامل > 6h
        if total_hours <= 0:
            dist = {"working": 0.0, "idle": 0.0, "on_phone": 0.0}
        elif total_hours < 6:
            dist = {"working": total_hours * 0.7, "idle": total_hours * 0.25, "on_phone": total_hours * 0.05}
        else:
            dist = {"working": total_hours * 0.8, "idle": total_hours * 0.15, "on_phone": total_hours * 0.05}
        productive = float(dist.get("working", 0.0))
        phone_t = float(dist.get("on_phone", 0.0))
        break_t = float(dist.get("idle", 0.0))
        rate = 0.0 if total_hours <= 0 else productive / max(total_hours, 1e-6)
        return {
            "total_work_time": total_hours,
            "productive_time": productive,
            "break_time": break_t,
            "phone_time": phone_t,
            "productivity_rate": float(rate),
            "activity_distribution": dist,
        }

    def compare_employees(self, d: date | str) -> pd.DataFrame:
        """مقارنة أداء الموظفين في يوم واحد باستخدام ساعات العمل من AttendanceSystem."""
        d_str = d if isinstance(d, str) else d.isoformat()
        rows = self.attendance.get_daily_attendance(d_str)
        emp_ids = sorted({r["employee_id"] for r in rows})
        records: List[Dict[str, object]] = []
        for eid in emp_ids:
            hours = self.attendance.calculate_work_hours(eid, d_str)
            records.append({"employee_id": eid, "total_hours": hours})
        df = pd.DataFrame(records)
        df.sort_values(by="total_hours", ascending=False, inplace=True)
        return df

    def detect_patterns(self, employee_id: str, days: int = 7) -> Dict[str, object]:
        """كشف أنماط مبسطة: أكثر ساعات إنتاجية وأوقات الراحة المتكررة خلال آخر N أيام."""
        today = date.today()
        hrs = []
        for i in range(days):
            d = date.fromordinal(today.toordinal() - i)
            h = self.attendance.calculate_work_hours(employee_id, d)
            hrs.append((d.isoformat(), h))
        hrs.sort()
        # تواريخ الأعلى والأقل
        top = max(hrs, key=lambda x: x[1]) if hrs else (None, 0)
        low = min(hrs, key=lambda x: x[1]) if hrs else (None, 0)
        return {
            "hours_series": hrs,
            "best_day": top,
            "worst_day": low,
        }

    def generate_insights(self, employee_id: str, period: str = "week") -> List[str]:
        """توليد رؤى نصية مبسطة."""
        insights: List[str] = []
        patt = self.detect_patterns(employee_id, days=7 if period == "week" else 30)
        hours = [h for _, h in patt.get("hours_series", [])]
        if not hours:
            return ["لا توجد بيانات كافية للرؤى"]
        avg = float(np.mean(hours))
        if avg < 4:
            insights.append("متوسط ساعات العمل منخفض هذا الأسبوع. يُنصح بالتحقق من أسباب الانخفاض.")
        else:
            insights.append("ساعات العمل ضمن المعدل المتوقع.")
        best_day = patt.get("best_day")
        if best_day and best_day[1] >= avg * 1.2:
            insights.append(f"يوم قوي: {best_day[0]} بساعات {best_day[1]:.1f}، حاول تكرار ظروف هذا اليوم.")
        return insights
