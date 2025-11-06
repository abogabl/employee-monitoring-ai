from __future__ import annotations

import numpy as np
import pytest

from src.activity_recognition import ActivityRecognizer


def test_activity_classifier_basic():
    ar = ActivityRecognizer(use_pose=False, use_objects=False, use_motion=False)
    pose = {"sitting": True, "hand_near_face": False, "hands_forward": True, "body_angle": 0.0, "pose_confidence": 1.0}
    objs = {"phone_nearby": False, "computer_nearby": True, "objects_list": []}
    res = ar.classify_activity(pose, objs, motion_level=0.2)
    assert res.activity in {"working", "idle", "on_phone", "meeting", "away"}
