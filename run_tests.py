"""
مشغل اختبارات مرن باستخدام pytest.
الاستخدام:
python run_tests.py --all
python run_tests.py --quick
python run_tests.py --coverage
"""
from __future__ import annotations

import argparse
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="تشغيل الاختبارات")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="تشغيل كل الاختبارات")
    group.add_argument("--quick", action="store_true", help="اختبارات سريعة فقط (وحدات)")
    group.add_argument("--coverage", action="store_true", help="تشغيل مع تغطية")
    args = parser.parse_args()

    cmd = [sys.executable, "-m", "pytest"]
    if args.quick:
        cmd += ["tests/unit"]
    elif args.coverage:
        cmd += ["--cov=src", "--cov-branch", "--cov-report=term-missing", "tests"]
    else:
        cmd += ["tests"]

    sys.exit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
