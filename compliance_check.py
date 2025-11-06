"""
compliance_check.py
فحص الامتثال (مثال: GDPR)
الاستخدام:
python compliance_check.py --standard gdpr
"""
from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Tuple

import psutil

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("compliance_check")


def check_consent_documents() -> Tuple[bool, str]:
    # تحقق من وجود وثائق الخصوصية واتفاقية المعالجة
    ok1 = Path("docs/privacy_policy.md").exists()
    ok2 = Path("docs/data_processing_agreement.md").exists()
    if ok1 and ok2:
        return True, "Privacy policy and DPA exist"
    return False, "Missing privacy_policy.md or data_processing_agreement.md"


def check_encryption_enabled() -> Tuple[bool, str]:
    p = Path("config/security_config.json")
    if not p.exists():
        return False, "security_config.json missing"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        enc = data.get("encryption", {})
        if enc.get("enabled") and Path(enc.get("key_file", "keys/encryption.key")).exists():
            return True, "Encryption enabled with key file"
        return False, "Encryption disabled or key file missing"
    except Exception as e:
        return False, f"Invalid security_config.json: {e}"


def check_access_logs() -> Tuple[bool, str]:
    p = Path("logs/audit.log")
    return (p.exists(), "Access logs present" if p.exists() else "Access logs missing")


def check_data_retention() -> Tuple[bool, str]:
    p = Path("config/security_config.json")
    if not p.exists():
        return False, "security_config.json missing"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        ret = data.get("data_retention", {})
        keys = {"attendance_logs", "video_recordings", "reports", "audit_logs"}
        if keys.issubset(ret.keys()):
            return True, "Retention policy configured"
        return False, "Incomplete retention policy"
    except Exception as e:
        return False, f"Invalid retention policy: {e}"


def check_system_health_caps() -> Tuple[bool, str]:
    # ذاكرة أقل من 80%، CPU أقل من 90% (تحقق لحظي)
    cpu = psutil.cpu_percent(interval=0.3)
    mem = psutil.virtual_memory().percent
    ok = (cpu < 90.0) and (mem < 80.0)
    return ok, f"CPU={cpu:.0f}%, MEM={mem:.0f}%"


def check_configs_valid() -> Tuple[bool, str]:
    problems: List[str] = []
    for cfg in ["config.json", "config/cameras_config.json", "config/alerts_config.json", "config/security_config.json"]:
        p = Path(cfg)
        if p.exists() and p.suffix == ".json":
            try:
                json.loads(p.read_text(encoding="utf-8"))
            except Exception as e:
                problems.append(f"{cfg}: {e}")
    return (len(problems) == 0, "Configs valid" if not problems else "; ".join(problems))


def check_network_connectivity() -> Tuple[bool, str]:
    # فحص بسيط: وجود اتصال DNS (محاولة حل اسم)
    try:
        import socket
        socket.gethostbyname("example.com")
        return True, "DNS OK"
    except Exception as e:
        return False, f"Network check failed: {e}"


def run_gdpr_checks() -> Dict[str, Dict[str, str]]:
    checks = {
        "consent_docs": check_consent_documents(),
        "encryption": check_encryption_enabled(),
        "access_logs": check_access_logs(),
        "retention": check_data_retention(),
        "system_caps": check_system_health_caps(),
        "configs": check_configs_valid(),
        "network": check_network_connectivity(),
    }
    result = {}
    for name, (ok, msg) in checks.items():
        result[name] = {"ok": str(ok), "info": msg}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="فحص الامتثال")
    parser.add_argument("--standard", choices=["gdpr"], required=True)
    args = parser.parse_args()

    if args.standard == "gdpr":
        res = run_gdpr_checks()
        failed = [k for k, v in res.items() if v["ok"] != "True"]
        for k, v in res.items():
            logger.info("%s: %s - %s", k, v["ok"], v["info"])
        if failed:
            logger.error("فشل الفحص في العناصر: %s", ", ".join(failed))
            raise SystemExit(1)
        else:
            logger.info("GDPR compliance checks passed")


if __name__ == "__main__":
    main()
