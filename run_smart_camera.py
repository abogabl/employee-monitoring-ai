#!/usr/bin/env python3
"""
سكريبت تشغيل الكاميرا الذكية المحسنة
يستخدم نفس التحسينات من المعالج الذكي للفيديو

استخدام:
python run_smart_camera.py                           # كاميرا افتراضية
python run_smart_camera.py --source 1               # كاميرا رقم 1  
python run_smart_camera.py --source video.mp4       # ملف فيديو
python run_smart_camera.py --camera-id office_cam   # كاميرا مكتب
"""

import sys
from pathlib import Path

# إضافة المجلد الجذر للمشروع
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from src.main_production_smart import main

if __name__ == "__main__":
    main()
