"""
ReportVisualizer: إنشاء رسوم بيانية للتقارير باستخدام matplotlib/seaborn ولوحة HTML بسيطة.
"""
from __future__ import annotations

import base64
import io
import logging
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

try:
    import matplotlib.pyplot as plt  # type: ignore
    import seaborn as sns  # type: ignore
    HAS_PLOT = True
except Exception:
    HAS_PLOT = False

from .activity_analyzer import ActivityAnalyzer
from .attendance_system import AttendanceSystem

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


class ReportVisualizer:
    """مولد الرسوم البيانية للتقارير."""

    def __init__(self, attendance: Optional[AttendanceSystem] = None, analyzer: Optional[ActivityAnalyzer] = None) -> None:
        self.attendance = attendance or AttendanceSystem()
        self.analyzer = analyzer or ActivityAnalyzer(self.attendance)
        if not HAS_PLOT:
            logger.warning("matplotlib/seaborn غير متاحين؛ ستُنشأ ملفات HTML بدون رسوم.")

    def _fig_to_base64(self) -> str:
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png", dpi=120)
        plt.close()
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("ascii")

    def activity_distribution_pie(self, employee_id: str, d: date | str) -> Optional[str]:
        if not HAS_PLOT:
            return None
        stats = self.analyzer.analyze_employee_day(employee_id, d)
        dist: Dict[str, float] = stats.get("activity_distribution", {})  # type: ignore
        if not dist:
            return None
        labels = list(dist.keys())
        sizes = list(dist.values())
        plt.figure(figsize=(4, 4))
        plt.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=140)
        plt.title(f"Activity Distribution {employee_id} @ {d}")
        return self._fig_to_base64()

    def productivity_timeline(self, employee_id: str, days: int = 7) -> Optional[str]:
        if not HAS_PLOT:
            return None
        patt = self.analyzer.detect_patterns(employee_id, days=days)
        series = patt.get("hours_series", [])  # type: ignore
        if not series:
            return None
        xs = [s for s, _ in series]
        ys = [h for _, h in series]
        plt.figure(figsize=(6, 3))
        plt.plot(xs, ys, marker="o")
        plt.xticks(rotation=45, ha="right")
        plt.ylabel("Hours")
        plt.title(f"Work Hours Timeline ({employee_id})")
        return self._fig_to_base64()

    def employee_comparison_bar(self, d: date | str) -> Optional[str]:
        if not HAS_PLOT:
            return None
        df = self.analyzer.compare_employees(d)
        if df.empty:
            return None
        plt.figure(figsize=(6, 3))
        plt.bar(df["employee_id"], df["total_hours"])  # type: ignore[index]
        plt.ylabel("Hours")
        plt.title(f"Employees Comparison @ {d}")
        plt.xticks(rotation=45, ha="right")
        return self._fig_to_base64()

    def hourly_activity_heatmap(self, employee_id: str, d: date | str) -> Optional[str]:
        if not HAS_PLOT:
            return None
        # نموذج مرجعي: سننشئ مصفوفة عشوائية صفرية هنا. يمكن لاحقاً ربطها بوقت النشاط الحقيقي من TimeTracker.
        import numpy as np
        mat = np.zeros((24, 3))  # [working, idle, on_phone]
        # ضع ساعات العمل التقريبية كقيمة نموذجية
        stats = self.analyzer.analyze_employee_day(employee_id, d)
        total = stats.get("total_work_time", 0.0)  # type: ignore
        hours = int(min(8, total))
        mat[9:9+hours, 0] = 1  # working
        plt.figure(figsize=(6, 4))
        sns.heatmap(mat, cmap="YlGnBu", cbar=False)
        plt.yticks(range(0, 24, 2), [f"{h:02d}:00" for h in range(0, 24, 2)])
        plt.xticks([0.5, 1.5, 2.5], ["working", "idle", "on_phone"])
        plt.title(f"Hourly Activity Heatmap ({employee_id} @ {d})")
        return self._fig_to_base64()

    def create_dashboard(self, data: Dict[str, str], output_path: str | Path = "reports/dashboard.html") -> str:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        # data يحتوي مفاتيح اختيارية: pie, timeline, bar, heatmap كـ base64
        html = ["<html><head><meta charset='utf-8'><title>Dashboard</title></head><body>"]
        html.append("<h2>Dashboard</h2>")
        for key, title in [("pie", "Activity Distribution"), ("timeline", "Productivity Timeline"), ("bar", "Employees Comparison"), ("heatmap", "Hourly Activity Heatmap")]:
            img = data.get(key)
            if img:
                html.append(f"<h3>{title}</h3>")
                html.append(f"<img src='data:image/png;base64,{img}' style='max-width: 100%;' />")
        html.append("</body></html>")
        out.write_text("\n".join(html), encoding="utf-8")
        logger.info("تم إنشاء لوحة HTML: %s", out)
        return str(out)
