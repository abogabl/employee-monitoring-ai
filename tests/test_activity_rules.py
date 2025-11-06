from __future__ import annotations

import math

from src.activity_rules import ActivityRules


def test_numeric_condition_ranges():
    rules = ActivityRules()
    assert rules._eval_numeric_condition(0.1, "<0.2") is True
    assert rules._eval_numeric_condition(0.3, "<0.2") is False
    assert rules._eval_numeric_condition(0.2, "0.1-0.4") is True
    assert rules._eval_numeric_condition(0.5, "0.1-0.4") is False
    assert rules._eval_numeric_condition(0.5, ">0.4") is True


def test_classify_on_phone():
    rules = ActivityRules()
    features = {
        "hand_near_face": True,
        "phone_nearby": True,
        "motion_level": 0.1,
        "sitting": False,
        "computer_nearby": False,
        "hands_forward": False,
    }
    act, score, _ = rules.classify(features)
    assert act == "on_phone"
    assert score >= 0.8  # min_score


def test_classify_working():
    rules = ActivityRules()
    features = {
        "sitting": True,
        "computer_nearby": True,
        "hands_forward": True,
        "motion_level": 0.2,
        "hand_near_face": False,
        "phone_nearby": False,
    }
    act, score, _ = rules.classify(features)
    assert act == "working"
    assert score >= 0.7
