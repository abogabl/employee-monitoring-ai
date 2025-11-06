from __future__ import annotations

import pytest
import numpy as np

pytest.importorskip("ultralytics")

from src.detection_tracking import PersonDetector, PersonTracker


def test_full_pipeline_smoke():
    # إطار صناعي
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    det = PersonDetector(model_size="n", device="cpu", conf=0.5, imgsz=320, half=False)
    tr = PersonTracker(max_disappeared=2, max_distance=80)

    dets = det.detect(frame)
    tracks = tr.update(dets)

    assert isinstance(dets, list)
    assert isinstance(tracks, dict)
