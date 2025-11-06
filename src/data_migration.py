"""
أداة ترحيل البيانات بين الإصدارات.
تشغيل:
python src/data_migration.py --from v1.0 --to v2.0
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Callable, Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("data_migration")


def migrate_v1_to_v2(project_root: Path) -> None:
    """مثال ترحيل: تحويل employees.json إلى تنسيق جديد إن لزم."""
    emp_path = project_root / "employees_database" / "employees.json"
    if not emp_path.exists():
        logger.info("لا يوجد employees.json للترحيل")
        return
    try:
        data = json.loads(emp_path.read_text(encoding="utf-8"))
        # مثال تحويلي: ضمان وجود حقل active للجميع
        changed = False
        for emp_id, info in data.items():
            if "active" not in info:
                info["active"] = True
                changed = True
        if changed:
            emp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info("تم تحديث employees.json بإضافة حقل active المفقود")
    except Exception as e:
        logger.exception("فشل ترحيل employees.json: %s", e)


MIGRATIONS: Dict[tuple[str, str], Callable[[Path], None]] = {
    ("v1.0", "v2.0"): migrate_v1_to_v2,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="ترحيل البيانات بين الإصدارات")
    parser.add_argument("--from", dest="src", required=True)
    parser.add_argument("--to", dest="dst", required=True)
    args = parser.parse_args()

    project_root = Path(".").resolve()
    key = (args.src, args.dst)
    fn = MIGRATIONS.get(key)
    if not fn:
        logger.error("لا يوجد ترحيل معرف من %s إلى %s", args.src, args.dst)
        return
    logger.info("بدء الترحيل من %s إلى %s", args.src, args.dst)
    fn(project_root)
    logger.info("اكتمل الترحيل")


if __name__ == "__main__":
    main()
