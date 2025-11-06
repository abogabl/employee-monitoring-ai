"""
تشغيل تطبيق الويب.
مثال:
python run_web_app.py --host 0.0.0.0 --port 5000 --debug
"""
from __future__ import annotations

import argparse

from web_app.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="تشغيل واجهة الويب")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
