"""
قواعد تصنيف الأنشطة بنظام نقاط قابل للتعديل.
يوفر تحميل/تهيئة القواعد وحساب درجة النشاط وفق خصائص مستخرجة.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


# الأنشطة القياسية
DEFAULT_ACTIVITIES = ["working", "on_phone", "sleeping", "idle", "meeting", "away"]


DEFAULT_RULES: Dict[str, Dict[str, Any]] = {
    "working": {
        "conditions": [
            {"sitting": True, "weight": 0.4},
            {"computer_nearby": True, "weight": 1.0},  # أهم شرط
            {"hands_forward": True, "weight": 0.5},
            {"motion_level": "0.01-0.6", "weight": 0.3},
        ],
        "min_score": 0.4,  # خفضنا الحد أكثر
    },
    "on_phone": {
        "conditions": [
            {"hand_near_face": True, "weight": 0.8},
            {"phone_nearby": True, "weight": 0.7},
            {"sitting": True, "weight": 0.3},
            {"motion_level": "<0.3", "weight": 0.3},
        ],
        "min_score": 0.6,  # خفضنا الحد
    },
    "sleeping": {
        "conditions": [
            {"sitting": True, "weight": 0.5},
            {"hand_near_face": True, "weight": 0.7},  # رأس على اليد
            {"motion_level": "<0.02", "weight": 0.9},  # حركة شبه معدومة
        ],
        "min_score": 0.7,  # نرفع الحد قليلاً لتقليل False Positives
    },
    "idle": {
        "conditions": [
            {"sitting": True, "weight": 0.5},
            {"motion_level": "<0.08", "weight": 0.6},
        ],
        "min_score": 0.4,  # خفضنا الحد
    },
    "meeting": {
        "conditions": [
            {"sitting": True, "weight": 0.4},
            {"motion_level": "0.05-0.4", "weight": 0.4},
            {"hands_forward": True, "weight": 0.3},
        ],
        "min_score": 0.5,
    },
    "away": {
        "conditions": [
            {"no_person": True, "weight": 1.0},
        ],
        "min_score": 0.9,
    },
}


@dataclass
class RuleScore:
    activity: str
    score: float
    passed: bool


class ActivityRules:
    """مدير قواعد تصنيف النشاط مع نظام نقاط/أوزان.

    يمكن تحميل القواعد من ملف JSON أو استخدام القواعد الافتراضية.
    تنسيق كل نشاط:
    {
      "conditions": [
        {"feature": value أو شرط بنطاق مثل '0.1-0.4' أو '<0.2', "weight": 0.7},
      ],
      "min_score": 0.7
    }
    """

    def __init__(self, rules: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
        self.rules = rules or DEFAULT_RULES.copy()

    @staticmethod
    def _eval_numeric_condition(value: float, cond: str) -> bool:
        """تقييم شرط عددي منسق مثل '<0.2' أو '0.1-0.4'."""
        cond = cond.strip()
        try:
            if "-" in cond:
                low_s, high_s = cond.split("-", 1)
                low = float(low_s)
                high = float(high_s)
                return low <= value <= high
            if cond.startswith("<"):
                thr = float(cond[1:])
                return value < thr
            if cond.startswith(">"):
                thr = float(cond[1:])
                return value > thr
        except Exception:
            logger.warning("شرط عددي غير صالح: %s", cond)
        return False

    def score_activity(self, activity: str, features: Dict[str, Any]) -> RuleScore:
        """حساب درجة نشاط واحد بناءً على الميزات extracted features."""
        rule = self.rules.get(activity, {})
        conditions: List[Dict[str, Any]] = rule.get("conditions", [])
        min_score: float = float(rule.get("min_score", 0.0))

        score = 0.0
        for cond in conditions:
            weight = float(cond.get("weight", 0.0))
            # مفتاح واحد منطقي/عددي في كل شرط
            key = next((k for k in cond.keys() if k not in {"weight"}), None)
            if key is None:
                continue
            expected = cond[key]
            val = features.get(key)
            ok = False
            if isinstance(expected, bool):
                ok = bool(val) is expected
            elif isinstance(expected, str) and isinstance(val, (int, float)):
                ok = self._eval_numeric_condition(float(val), expected)
            # إضافة الوزن عند تحقق الشرط
            if ok:
                score += weight

        return RuleScore(activity=activity, score=score, passed=score >= min_score)

    def classify(self, features: Dict[str, Any]) -> Tuple[str, float, Dict[str, float]]:
        """إرجاع أفضل نشاط بالاعتماد على أعلى درجة تتجاوز الحد الأدنى."""
        scores: Dict[str, RuleScore] = {
            act: self.score_activity(act, features) for act in self.rules.keys()
        }
        # اختيار الأعلى الذي تجاوز الحد الأدنى وإلا أعلى مطلقاً
        valid = [rs for rs in scores.values() if rs.passed]
        if valid:
            best = max(valid, key=lambda r: r.score)
        else:
            best = max(scores.values(), key=lambda r: r.score)
        return best.activity, best.score, {k: v.score for k, v in scores.items()}

    @classmethod
    def from_json(cls, path: str | Path) -> "ActivityRules":
        """تحميل قواعد من ملف JSON."""
        p = Path(path)
        if not p.exists():
            logger.warning("ملف القواعد غير موجود: %s، سيتم استخدام القواعد الافتراضية.", p)
            return cls()
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("صيغة القواعد غير صحيحة")
            return cls(rules=data)
        except Exception as e:
            logger.exception("تعذر قراءة القواعد من %s: %s", p, e)
            return cls()

    def to_json(self, path: str | Path) -> None:
        """حفظ القواعد إلى ملف JSON."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        try:
            p.write_text(json.dumps(self.rules, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.exception("تعذر حفظ القواعد إلى %s: %s", p, e)
