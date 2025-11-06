from __future__ import annotations

import numpy as np
from src.detection_tracking import PersonTracker


def test_tracker_register_and_update():
    tr = PersonTracker(max_disappeared=2, max_distance=100)
    # إدخال كشفين في إطار واحد
    dets = [
        {"box": (10, 10, 50, 50)},
        {"box": (200, 200, 260, 260)},
    ]
    tracks = tr.update(dets)
    assert len(tracks) == 2
    ids = list(tracks.keys())
    # تحريك بسيط داخل المسافة
    dets2 = [
        {"box": (15, 15, 55, 55)},
        {"box": (205, 205, 265, 265)},
    ]
    tracks2 = tr.update(dets2)
    assert set(tracks2.keys()) == set(ids)


def test_tracker_disappearance_and_removal():
    tr = PersonTracker(max_disappeared=1, max_distance=50)
    tracks = tr.update([{ "box": (0,0,10,10)}])
    tid = next(iter(tracks.keys()))
    # إطار بدون كاشفات -> اختفاء 1
    tr.update([])
    # إطار ثانٍ بدون كاشفات -> يحذف
    tr.update([])
    assert tid not in tr.tracks
