from __future__ import annotations

import time
import pytest
import numpy as np

pytest.importorskip("ultralytics")

from src.detection_tracking import PersonDetector


def test_yolo_init_cpu():
    det = PersonDetector(model_size="n", device="cpu", conf=0.5, imgsz=320, half=False)
    assert det is not None


def test_detect_on_blank_image_fast():
    det = PersonDetector(model_size="n", device="cpu", conf=0.5, imgsz=320, half=False)
    img = np.zeros((320, 320, 3), dtype=np.uint8)
    t0 = time.time()
    dets = det.detect(img)
    dt = time.time() - t0
    assert isinstance(dets, list)
    assert dt < 1.5  # ثواني، لضمان السرعة الأساسية
