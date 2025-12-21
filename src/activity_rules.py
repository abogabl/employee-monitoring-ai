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
            {"sitting": True, "weight": 0.3},
            {"computer_nearby": True, "weight": 1.2},  # Increased weight for computer
            {"hands_forward": True, "weight": 0.5},
            {"motion_level": "0.01-0.6", "weight": 0.4},
        ],
        "min_score": 0.45,
    },
    "on_phone": {
        "conditions": [
            {"hand_near_face": True, "weight": 0.9},
            {"phone_nearby": True, "weight": 0.8},
            {"sitting": True, "weight": 0.2},
            {"motion_level": "<0.3", "weight": 0.3},
        ],
        "min_score": 0.65,
    },
    "sleeping": {
        "conditions": [
            {"sitting": True, "weight": 0.4},
            {"hand_near_face": True, "weight": 0.6},
            {"motion_level": "<0.015", "weight": 1.0},  # Stricter motion for sleeping
        ],
        "min_score": 0.75,
    },
    "idle": {
        "conditions": [
            {"sitting": True, "weight": 0.6},
            {"motion_level": "<0.05", "weight": 0.5},
        ],
        "min_score": 0.45,
    },
    "meeting": {
        "conditions": [
            {"sitting": True, "weight": 0.3},
            {"motion_level": "0.05-0.3", "weight": 0.3},
            {"hands_forward": True, "weight": 0.2},
        ],
        "min_score": 1.5,  # Increased to effectively disable unless specifically tuned later
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

    def __init__(self, rules: Optional[Dict[str, Dict[str, Any]]] = None, config_path: Optional[str] = None) -> None:
        self.rules = rules or DEFAULT_RULES.copy()
        self.config = self._load_activity_config(config_path)
        self._update_rules_from_config()

    def _load_activity_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """تحميل إعدادات النشاط من ملف JSON."""
        if config_path is None:
            config_path = "config/activity_config.json"
        
        config_file = Path(config_path)
        if not config_file.exists():
            logger.info("ملف إعدادات النشاط غير موجود: %s، سيتم استخدام الإعدادات الافتراضية", config_path)
            return {}
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info("تم تحميل إعدادات النشاط من: %s", config_path)
            return config
        except Exception as e:
            logger.warning("فشل تحميل إعدادات النشاط: %s", e)
            return {}

    def _update_rules_from_config(self) -> None:
        """تحديث القواعد باستخدام الإعدادات المحملة."""
        if not self.config:
            return
        
        # تحديث عتبات الكشف للهاتف
        phone_config = self.config.get("phone_detection", {})
        if "on_phone" in self.rules and phone_config:
            phone_rule = self.rules["on_phone"]
            if "distance_ratio" in phone_config:
                # تحديث وزن phone_nearby بناءً على distance_ratio
                for cond in phone_rule.get("conditions", []):
                    if "phone_nearby" in cond:
                        cond["weight"] = phone_config["distance_ratio"] * 1.5
        
        # تحديث عتبات النوم
        sleep_config = self.config.get("sleep_detection", {})
        if "sleeping" in self.rules and sleep_config:
            sleep_rule = self.rules["sleeping"]
            if "head_angle_threshold" in sleep_config:
                sleep_rule["min_score"] = max(0.6, sleep_config["head_angle_threshold"] / 40.0)
        
        # تحديث عتبات العمل
        work_config = self.config.get("working_detection", {})
        if "working" in self.rules and work_config:
            work_rule = self.rules["working"]
            if "motion_level_min" in work_config:
                for cond in work_rule.get("conditions", []):
                    if "motion_level" in cond:
                        min_motion = work_config["motion_level_min"]
                        cond["motion_level"] = f"{min_motion}-0.8"

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
