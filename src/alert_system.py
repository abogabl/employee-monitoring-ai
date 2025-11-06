"""
AlertSystem: فحص القواعد وإرسال التنبيهات عبر قنوات متعددة مع سجل وتخفيض التكرار.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .alert_history import AlertHistory
from .attendance_system import AttendanceSystem
from .camera_health_monitor import CameraHealthMonitor
from .employee_manager import EmployeeDatabase
from .notification_channels import EmailNotifier, TelegramNotifier, WebhookNotifier
from .activity_analyzer import ActivityAnalyzer

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


PRIORITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


@dataclass
class AlertRule:
    enabled: bool
    priority: str
    channels: List[str]
    params: Dict[str, Any]


class AlertSystem:
    def __init__(self, config_path: str | Path = "config/alerts_config.json") -> None:
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.enabled = True
        self.check_interval = 60
        self.rules: Dict[str, AlertRule] = {}
        self.history = AlertHistory()
        self.attendance = AttendanceSystem()
        self.employees = EmployeeDatabase()
        self.health = CameraHealthMonitor()
        self.analyzer = ActivityAnalyzer(self.attendance)
        # قنوات
        self.email: Optional[EmailNotifier] = None
        self.telegram: Optional[TelegramNotifier] = None
        self.webhook: Optional[WebhookNotifier] = None
        # منع التكرار
        self.last_sent: Dict[Tuple[str, str], float] = {}  # (type, key) -> ts
        self.cooldown_seconds = 300
        self.load_config()

    # ---------------- Config ----------------
    def load_config(self) -> None:
        if not self.config_path.exists():
            logger.warning("alerts_config.json غير موجود، سيتم استخدام قيم افتراضية")
            self.config = {}
            return
        self.config = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.enabled = bool(self.config.get("enabled", True))
        self.check_interval = int(self.config.get("check_interval", 60))
        self.cooldown_seconds = int(self.config.get("cooldown", 300))
        ch = self.config.get("channels", {})
        if ch.get("email", {}).get("enabled"):
            c = ch["email"]
            self.email = EmailNotifier(c.get("smtp_server", ""), int(c.get("smtp_port", 587)), c.get("sender", "noreply@example.com"))
        if ch.get("telegram", {}).get("enabled"):
            c = ch["telegram"]
            self.telegram = TelegramNotifier(c.get("bot_token", ""), c.get("chat_ids", []))
        if ch.get("webhook", {}).get("enabled"):
            c = ch["webhook"]
            self.webhook = WebhookNotifier(c.get("url", ""), headers=c.get("headers", {}))
        # rules
        self.rules = {}
        r = self.config.get("rules", {})
        # late_employee
        if r.get("late_employee", {}).get("enabled", False):
            rr = r["late_employee"]
            self.rules["late_employee"] = AlertRule(True, rr.get("priority", "MEDIUM"), rr.get("channels", []), {"threshold_minutes": int(rr.get("threshold_minutes", 15))})
        # camera_down
        if r.get("camera_down", {}).get("enabled", False):
            rr = r["camera_down"]
            self.rules["camera_down"] = AlertRule(True, rr.get("priority", "HIGH"), rr.get("channels", []), {})
        # unknown_face
        if r.get("unknown_face", {}).get("enabled", False):
            rr = r["unknown_face"]
            self.rules["unknown_face"] = AlertRule(True, rr.get("priority", "HIGH"), rr.get("channels", []), {"max_count": int(rr.get("max_count", 3))})
        # low_productivity
        if r.get("low_productivity", {}).get("enabled", False):
            rr = r["low_productivity"]
            self.rules["low_productivity"] = AlertRule(True, rr.get("priority", "MEDIUM"), rr.get("channels", []), {"threshold": float(rr.get("threshold", 0.5))})

    # ---------------- Checks ----------------
    def check_late_employees(self, expected_time: str = "09:00") -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        try:
            late = self.attendance.get_late_employees(d=None, expected_time=expected_time)
            for r in late:
                msg = f"موظف متأخر: {r['employee_id']} ({r['employee_name']}) first_in={r['first_check_in']}"
                results.append({"type": "late_employee", "msg": msg, "key": r["employee_id"]})
        except Exception as e:
            logger.warning("check_late_employees failed: %s", e)
        return results

    def check_absent_employees(self, d: date | None = None) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        d = d or date.today()
        try:
            rows = self.attendance.get_daily_attendance(d)
            present_ids = {r["employee_id"] for r in rows}
            # كل الموظفين
            all_emp = {e["emp_id"] for e in self.employees.list_all_employees()}
            absent = all_emp - present_ids
            for emp in absent:
                msg = f"موظف غائب: {emp} في {d}"
                results.append({"type": "absent", "msg": msg, "key": emp})
        except Exception as e:
            logger.warning("check_absent_employees failed: %s", e)
        return results

    def check_low_productivity(self, threshold: float = 0.5) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        try:
            rows = self.attendance.get_daily_attendance(date.today())
            emp_ids = sorted({r["employee_id"] for r in rows})
            for eid in emp_ids:
                stats = self.analyzer.analyze_employee_day(eid, date.today())
                rate = float(stats.get("productivity_rate", 0.0))
                if rate < threshold:
                    results.append({"type": "low_productivity", "msg": f"إنتاجية منخفضة: {eid} rate={rate:.2f}", "key": eid})
        except Exception as e:
            logger.warning("check_low_productivity failed: %s", e)
        return results

    def check_unknown_faces(self, max_unknown: int = 5) -> List[Dict[str, Any]]:
        # يحتاج تكامل مع FaceRecognitionSystem لقراءة عداد الوجوه المجهولة. هنا قيمة مكانية.
        return []

    def check_camera_health(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        try:
            for cid, st in self.health.status.items():
                if not st.ok or st.frozen:
                    results.append({"type": "camera_down", "msg": f"Camera issue: {cid} - {st.message}", "key": cid})
        except Exception as e:
            logger.warning("check_camera_health failed: %s", e)
        return results

    # ---------------- Sending ----------------
    def _throttle(self, alert_type: str, key: str, now: float) -> bool:
        last = self.last_sent.get((alert_type, key))
        if last and (now - last) < self.cooldown_seconds:
            return True
        self.last_sent[(alert_type, key)] = now
        return False

    def send_alert(self, alert_type: str, message: str, priority: str = "MEDIUM", recipients: Optional[List[str]] = None) -> None:
        logger.info("[ALERT][%s][%s] %s", priority, alert_type, message)
        try:
            self.history.add_alert(alert_type, message, priority)
        except Exception:
            pass
        # قنوات حسب القاعدة
        rule = self.rules.get(alert_type)
        if not rule:
            return
        chs = rule.channels
        if "email" in chs and self.email and recipients:
            self.email.send(subject=f"[{priority}] {alert_type}", body=message, recipients=recipients)
        if "telegram" in chs and self.telegram:
            self.telegram.send_text(f"[{priority}] {alert_type}: {message}")
        if "webhook" in chs and self.webhook:
            self.webhook.post({"type": alert_type, "priority": priority, "message": message})

    # ---------------- Main check loop helper ----------------
    def run_checks_once(self) -> None:
        now = time.time()
        # Late employees
        if "late_employee" in self.rules:
            for r in self.check_late_employees():
                if self._throttle(r["type"], r["key"], now):
                    continue
                recipients = self.config.get("channels", {}).get("email", {}).get("recipients", [])
                self.send_alert(r["type"], r["msg"], self.rules["late_employee"].priority, recipients)
        # Camera health
        if "camera_down" in self.rules:
            for r in self.check_camera_health():
                if self._throttle(r["type"], r["key"], now):
                    continue
                self.send_alert(r["type"], r["msg"], self.rules["camera_down"].priority)
        # Low productivity
        if "low_productivity" in self.rules:
            thr = float(self.rules["low_productivity"].params.get("threshold", 0.5))
            for r in self.check_low_productivity(threshold=thr):
                if self._throttle(r["type"], r["key"], now):
                    continue
                self.send_alert(r["type"], r["msg"], self.rules["low_productivity"].priority)
