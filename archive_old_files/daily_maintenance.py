"""
تشغيل صيانة يومية مجمعة:
- نسخ احتياطي
- تنظيف ملفات قديمة
- تحسين قاعدة البيانات
- فحص سلامة البيانات
- إرسال تقرير صيانة عبر البريد (إن تم ضبط SMTP في alerts_config)

تشغيل تلقائي مع Windows Task Scheduler:
python daily_maintenance.py --auto
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

from src.backup_system import BackupSystem
from src.maintenance import MaintenanceManager
from src.reporting import ReportGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("daily_maintenance")


def load_email_settings() -> tuple[bool, dict]:
    cfg_path = Path("config/alerts_config.json")
    if not cfg_path.exists():
        return False, {}
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        email = data.get("channels", {}).get("email", {})
        if not email.get("enabled"):
            return False, {}
        return True, email
    except Exception:
        return False, {}


def main() -> None:
    parser = argparse.ArgumentParser(description="صيانة يومية")
    parser.add_argument("--auto", action="store_true", help="تشغيل كل المهام")
    args = parser.parse_args()

    root = Path(".").resolve()

    # 1) نسخ احتياطي
    backup = BackupSystem(root=root)
    backup_path = backup.create_backup("full")
    zip_path = backup.compress_backup(backup_path)
    backup.delete_old_backups(keep_days=30)

    # 2) صيانة وتنظيف
    mm = MaintenanceManager(project_root=root)
    removed_logs = mm.clean_old_logs(days=7)
    removed_reports = mm.clean_old_reports(days=90)
    mm.optimize_database()
    mm.rebuild_indexes()
    mm.vacuum_database()
    ok, errors = mm.verify_data_integrity()
    health = mm.check_system_health()

    # 3) تقرير صيانة
    report_lines = [
        f"Backup: {backup_path}",
        f"Compressed: {zip_path}",
        f"Removed logs: {removed_logs}",
        f"Removed reports: {removed_reports}",
        f"Integrity: {'OK' if ok else 'FAILED'}",
        f"Errors: {errors}",
        f"Health: CPU={health['cpu_percent']:.0f}%, MEM={health['mem_percent']:.0f}%, DiskFree={health['disk_free_gb']:.1f}GB",
    ]
    report_text = "\n".join(report_lines)
    out_txt = Path("reports") / f"maintenance_{datetime.now().date().isoformat()}.txt"
    out_txt.parent.mkdir(parents=True, exist_ok=True)
    out_txt.write_text(report_text, encoding="utf-8")
    logger.info("تم إنشاء تقرير الصيانة: %s", out_txt)

    # 4) إرسال عبر البريد (اختياري)
    enabled, email = load_email_settings()
    if enabled:
        try:
            rg = ReportGenerator()  # سنستخدم دالة الإرسال البسيطة داخله
            rg.send_email(
                to_email=", ".join(email.get("recipients", [])),
                subject=f"Maintenance Report {datetime.now().date().isoformat()}",
                body=report_text,
                attachments=[str(out_txt), str(zip_path)],
                smtp_server=email.get("smtp_server", ""),
                smtp_port=int(email.get("smtp_port", 587)),
                username=email.get("sender", ""),
                password=email.get("password", ""),
            )
        except Exception:
            logger.warning("فشل إرسال البريد لتقرير الصيانة")


if __name__ == "__main__":
    main()
