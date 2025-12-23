"""
ReportGenerator: توليد تقارير تفصيلية وملخصات يومية وتقارير موظف ومقارنات، مع مخرجات CSV/Excel/HTML/PDF.
- يدعم i18n عربي/إنجليزي بسيط عبر معجم تسميات.
- يستخدم AttendanceSystem وActivityAnalyzer كمصادر بيانات.
- يدعم إرسال التقارير بالبريد (اختياري) عبر SMTP.
"""
from __future__ import annotations

import csv
import logging
import smtplib
from dataclasses import dataclass
from datetime import date, datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

from .attendance_system import AttendanceSystem
from .activity_analyzer import ActivityAnalyzer

try:
    import matplotlib.pyplot as plt  # type: ignore
    from matplotlib.backends.backend_pdf import PdfPages  # type: ignore
    HAS_MPL = True
except Exception:
    HAS_MPL = False

try:
    import seaborn as sns  # type: ignore
    HAS_SEABORN = True
except Exception:
    HAS_SEABORN = False

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


I18N = {
    "ar": {
        "employee_id": "معرّف الموظف",
        "employee_name": "اسم الموظف",
        "camera_id": "الكاميرا",
        "activity": "النشاط",
        "start_time": "بداية",
        "end_time": "نهاية",
        "duration_seconds": "المدة (ثواني)",
        "duration_formatted": "المدة (س:د:ث)",
        "check_in_time": "وقت الدخول",
        "check_out_time": "وقت الخروج",
        "total_hours": "إجمالي الساعات",
        "working_hours": "ساعات العمل",
        "phone_hours": "ساعات الهاتف",
        "idle_hours": "ساعات الراحة",
        "productivity_rate": "معدل الإنتاجية",
        "status": "الحالة",
    },
    "en": {
        "employee_id": "employee_id",
        "employee_name": "employee_name",
        "camera_id": "camera_id",
        "activity": "activity",
        "start_time": "start_time",
        "end_time": "end_time",
        "duration_seconds": "duration_seconds",
        "duration_formatted": "duration_formatted",
        "check_in_time": "check_in_time",
        "check_out_time": "check_out_time",
        "total_hours": "total_hours",
        "working_hours": "working_hours",
        "phone_hours": "phone_hours",
        "idle_hours": "idle_hours",
        "productivity_rate": "productivity_rate",
        "status": "status",
    },
}


def _fmt_hhmmss(seconds: float) -> str:
    s = int(max(0, round(seconds)))
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    return f"{h:02d}:{m:02d}:{sec:02d}"


@dataclass
class ReportGenerator:
    attendance: AttendanceSystem = AttendanceSystem()
    analyzer: ActivityAnalyzer = ActivityAnalyzer()
    language: str = "ar"

    # --------------------- Detailed Segments Report ---------------------
    def generate_segments_report(self, data: Iterable[Dict[str, Any]], output_path: str | Path) -> str:
        """إنشاء تقرير المقاطع التفصيلية CSV/Excel حسب الامتداد."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for r in data:
            # توقع الحقول الأساسية في عناصر data
            duration = float(r.get("duration", r.get("duration_seconds", 0.0)))
            rows.append({
                "employee_id": r.get("employee_id", ""),
                "employee_name": r.get("employee_name", ""),
                "camera_id": r.get("camera_id", ""),
                "activity": r.get("activity", ""),
                "start_time": r.get("start_time"),
                "end_time": r.get("end_time"),
                "duration_seconds": duration,
                "duration_formatted": _fmt_hhmmss(duration),
            })
        df = pd.DataFrame(rows)
        self._save_table(df, out)
        logger.info("تم توليد تقرير المقاطع: %s", out)
        return str(out)

    # --------------------- Daily Summary Report ---------------------
    def generate_daily_summary(self, d: date | str, output_path: str | Path) -> str:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        d_str = d if isinstance(d, str) else d.isoformat()
        rows = self.attendance.get_daily_attendance(d_str)
        out_rows: List[Dict[str, Any]] = []
        for r in rows:
            eid = r.get("employee_id", "")
            ename = r.get("employee_name", eid)
            check_in = r.get("check_in_time")
            check_out = r.get("check_out_time")
            total_hours = float(self.attendance.calculate_work_hours(eid, d_str))
            # تقدير توزيع الأنشطة من ActivityAnalyzer (يمكن استبداله ببيانات أدق عند الربط مع TimeTracker)
            stats = self.analyzer.analyze_employee_day(eid, d_str)
            out_rows.append({
                "employee_id": eid,
                "employee_name": ename,
                "check_in_time": check_in,
                "check_out_time": check_out,
                "total_hours": round(total_hours, 2),
                "working_hours": round(float(stats.get("productive_time", 0.0)), 2),
                "phone_hours": round(float(stats.get("phone_time", 0.0)), 2),
                "idle_hours": round(float(stats.get("break_time", 0.0)), 2),
                "productivity_rate": round(float(stats.get("productivity_rate", 0.0)), 3),
                "status": r.get("status", "checked_out"),
            })
        df = pd.DataFrame(out_rows)
        self._save_table(df, out)
        logger.info("تم توليد ملخص اليوم: %s", out)
        return str(out)

    # --------------------- Employee Report ---------------------
    def generate_employee_report(self, employee_id: str, start_date: date | str, end_date: date | str) -> pd.DataFrame:
        rows = self.attendance.get_employee_attendance(employee_id, start_date, end_date)
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        # تحويل أزمنة إلى ساعات لكل سجل
        def _hrs(r):
            try:
                cin = pd.to_datetime(r.get("check_in_time")) if r.get("check_in_time") else None
                cout = pd.to_datetime(r.get("check_out_time")) if r.get("check_out_time") else None
                if cin is None:
                    return 0.0
                if cout is None:
                    cout = pd.Timestamp.now()
                return max(0.0, (cout - cin).total_seconds() / 3600.0)
            except Exception:
                return 0.0
        df["hours"] = df.apply(_hrs, axis=1)
        return df

    # --------------------- Visual Report (HTML/PDF) ---------------------
    def generate_visual_report(self, data: Dict[str, Any], output_path: str | Path) -> str:
        """تقرير بصري HTML أو PDF بسيط باستخدام matplotlib. إذا لم تتوفر matplotlib، سيتم إنشاء HTML بسيط فقط."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        ext = out.suffix.lower()
        if ext == ".pdf" and HAS_MPL:
            with PdfPages(str(out)) as pdf:
                fig, ax = plt.subplots(figsize=(8.5, 5))
                ax.axis('off')
                ax.text(0.5, 0.9, data.get("title", "Report"), ha='center', va='center', fontsize=16)
                ax.text(0.05, 0.8, data.get("subtitle", ""), fontsize=10)
                # جدول مختصر إذا توفر
                items = data.get("items", [])
                y = 0.7
                for it in items[:20]:
                    ax.text(0.05, y, str(it), fontsize=8)
                    y -= 0.035
                pdf.savefig(fig)
                plt.close(fig)
            logger.info("تم توليد تقرير PDF: %s", out)
            return str(out)
        else:
            # HTML بسيط
            html = ["<html><head><meta charset='utf-8'><title>Report</title></head><body>"]
            html.append(f"<h2>{data.get('title', 'Report')}</h2>")
            if data.get("subtitle"):
                html.append(f"<p>{data['subtitle']}</p>")
            if data.get("items"):
                html.append("<ul>")
                for it in data["items"]:
                    html.append(f"<li>{it}</li>")
                html.append("</ul>")
            html.append("</body></html>")
            out.write_text("\n".join(html), encoding="utf-8")
            logger.info("تم توليد تقرير HTML: %s", out)
            return str(out)

    # --------------------- حفظ جداول ---------------------
    def _save_table(self, df: pd.DataFrame, out: Path) -> None:
        if out.suffix.lower() == ".csv":
            df.to_csv(out, index=False, encoding="utf-8-sig")
        elif out.suffix.lower() in {".xlsx", ".xls"}:
            try:
                df.to_excel(out, index=False)
            except Exception as e:
                logger.warning("تعذر حفظ Excel، سيتم حفظ CSV بدلاً من ذلك: %s", e)
                df.to_csv(out.with_suffix(".csv"), index=False, encoding="utf-8-sig")
        else:
            # افتراضي CSV
            df.to_csv(out.with_suffix(".csv"), index=False, encoding="utf-8-sig")

    # --------------------- إرسال بريد ---------------------
    def send_email(self, to_email: str, subject: str, body: str, attachments: Optional[List[str]] = None, smtp_server: str = "", smtp_port: int = 587, username: str = "", password: str = "") -> bool:
        """إرسال بريد مع مرفقات. يتطلب خادم SMTP صالح. أمنياً: لا تخزن كلمات سر في المستودع."""
        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = username or "noreply@example.com"
            msg["To"] = to_email
            msg.set_content(body)
            for att in attachments or []:
                p = Path(att)
                if not p.exists():
                    continue
                data = p.read_bytes()
                msg.add_attachment(data, maintype="application", subtype="octet-stream", filename=p.name)
            if not smtp_server or not username or not password:
                logger.warning("SMTP غير مضبوط، لن يتم إرسال البريد.")
                return False
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(msg)
            logger.info("تم إرسال البريد إلى %s", to_email)
            return True
        except Exception as e:
            logger.exception("فشل إرسال البريد: %s", e)
            return False
