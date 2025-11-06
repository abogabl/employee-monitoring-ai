"""
تنظيف الملفات القديمة والمؤقتة.
مثال:
python cleanup.py --older-than 30 --dry-run
"""
from __future__ import annotations

import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("cleanup")


TARGETS = [
    ("videos", [".mp4", ".avi", ".mov", ".mkv"]),
    ("reports", [".csv", ".xlsx", ".xls", ".txt"]),
    ("logs", [".log", ".txt"]),
    (".cache", None),
    ("__pycache__", None),
]


def collect_files(root: Path, days: int) -> List[Path]:
    cutoff = datetime.now() - timedelta(days=days)
    found: List[Path] = []
    for folder, exts in TARGETS:
        p = root / folder
        if not p.exists():
            continue
        for f in p.rglob("*"):
            if f.is_file():
                if exts is None or f.suffix.lower() in exts:
                    try:
                        if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                            found.append(f)
                    except Exception:
                        continue
    return found


def main() -> None:
    ap = argparse.ArgumentParser(description="تنظيف الملفات القديمة")
    ap.add_argument("--older-than", type=int, default=30, help="أيام")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = Path(".").resolve()
    files = collect_files(root, args.older_than)
    logger.info("تم العثور على %d ملفات مرشحة للحذف", len(files))
    for f in files:
        logger.info("%s", f)
    if not args.dry_run:
        for f in files:
            try:
                f.unlink(missing_ok=True)
            except Exception:
                pass
        logger.info("تم حذف %d ملفات", len(files))


if __name__ == "__main__":
    main()
