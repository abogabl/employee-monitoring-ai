"""
MaintenanceManager: مهام الصيانة الدورية للنظام.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import psutil

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


class MaintenanceManager:
    def __init__(self, project_root: str | Path = ".") -> None:
        self.root = Path(project_root).resolve()
        self.logs_dir = self.root / "logs"
        self.reports_dir = self.root / "reports"
        self.attendance_db = self.root / "attendance_db" / "attendance.db"

    # ---------------- تنظيف ----------------
    def clean_old_logs(self, days: int = 7) -> int:
        cutoff = datetime.now() - timedelta(days=int(days))
        removed = 0
        if not self.logs_dir.exists():
            return 0
        for f in self.logs_dir.glob("**/*"):
            if f.is_file():
                try:
                    if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                        f.unlink(missing_ok=True)
                        removed += 1
                except Exception:
                    continue
        logger.info("تم حذف %d ملفات سجلات قديمة", removed)
        return removed

    def clean_old_reports(self, days: int = 90) -> int:
        cutoff = datetime.now() - timedelta(days=int(days))
        removed = 0
        if not self.reports_dir.exists():
            return 0
        for f in self.reports_dir.glob("**/*"):
            if f.is_file():
                try:
                    if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                        f.unlink(missing_ok=True)
                        removed += 1
                except Exception:
                    continue
        logger.info("تم حذف %d تقارير قديمة", removed)
        return removed

    # ---------------- قواعد بيانات ----------------
    def optimize_database(self) -> None:
        if not self.attendance_db.exists():
            return
        try:
            con = sqlite3.connect(str(self.attendance_db))
            cur = con.cursor()
            cur.execute("PRAGMA optimize")
            con.commit()
            con.close()
            logger.info("تم تشغيل PRAGMA optimize على attendance.db")
        except Exception as e:
            logger.warning("optimize_database فشل: %s", e)

    def rebuild_indexes(self) -> None:
        if not self.attendance_db.exists():
            return
        try:
            con = sqlite3.connect(str(self.attendance_db))
            cur = con.cursor()
            # إعادة إنشاء المؤشرات الأساسية
            cur.execute("CREATE INDEX IF NOT EXISTS idx_att_emp_date ON attendance_logs (employee_id, date)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_att_status ON attendance_logs (status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_att_date ON attendance_logs (date)")
            con.commit()
            con.close()
            logger.info("تم إعادة بناء المؤشرات")
        except Exception as e:
            logger.warning("rebuild_indexes فشل: %s", e)

    def vacuum_database(self) -> None:
        if not self.attendance_db.exists():
            return
        try:
            con = sqlite3.connect(str(self.attendance_db))
            cur = con.cursor()
            cur.execute("VACUUM")
            con.commit()
            con.close()
            logger.info("تم تنفيذ VACUUM")
        except Exception as e:
            logger.warning("vacuum_database فشل: %s", e)

    # ---------------- فحوصات ----------------
    def check_disk_space(self) -> float:
        total, used, free = shutil.disk_usage(self.root)
        gb_free = free / (1024 ** 3)
        logger.info("مساحة القرص الحرة: %.2f GB", gb_free)
        return gb_free

    def check_system_health(self) -> Dict[str, float]:
        cpu = float(psutil.cpu_percent(interval=0.2))
        mem = float(psutil.virtual_memory().percent)
        disk_free_gb = self.check_disk_space()
        return {"cpu_percent": cpu, "mem_percent": mem, "disk_free_gb": disk_free_gb}

    def verify_data_integrity(self) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        # تحقق من JSON الموظفين
        emp_json = self.root / "employees_database" / "employees.json"
        if emp_json.exists():
            try:
                json.loads(emp_json.read_text(encoding="utf-8"))
            except Exception as e:
                errors.append(f"employees.json غير صالح: {e}")
        # تحقق من وجود ملف التضمينات
        enc = self.root / "models" / "face_encodings.pkl"
        if enc.exists() and enc.stat().st_size <= 0:
            errors.append("ملف face_encodings.pkl فارغ")
        # تحقق من config.json
        cfg = self.root / "config.json"
        if cfg.exists():
            try:
                json.loads(cfg.read_text(encoding="utf-8"))
            except Exception as e:
                errors.append(f"config.json غير صالح: {e}")
        ok = len(errors) == 0
        logger.info("سلامة البيانات: %s", "OK" if ok else "; ".join(errors))
        return ok, errors
