"""
مدقق نتائج التعرف على الأنشطة: يحسب accuracy/precision/recall و confusion matrix.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


def load_ground_truth_csv(path: str | Path) -> List[Tuple[str, str]]:
    """تحميل ground truth من CSV بسيط بصيغة: track_id,activity."""
    p = Path(path)
    if not p.exists():
        logger.error("ملف ground truth غير موجود: %s", p)
        return []
    rows: List[Tuple[str, str]] = []
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.lower().startswith("track_id"):
                continue
            parts = [x.strip() for x in line.split(",")]
            if len(parts) >= 2:
                rows.append((parts[0], parts[1]))
    except Exception as e:
        logger.exception("تعذر قراءة ground truth: %s", e)
    return rows


def compute_metrics(y_true: Sequence[str], y_pred: Sequence[str], labels: Optional[List[str]] = None) -> Dict[str, object]:
    """حساب المقاييس القياسية والإرجاع كقاموس."""
    if labels is None:
        labels = sorted(list(set(y_true) | set(y_pred)))
    acc = float(accuracy_score(y_true, y_pred))
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    report = classification_report(y_true, y_pred, labels=labels, zero_division=0, output_dict=True)
    return {
        "accuracy": acc,
        "labels": labels,
        "confusion_matrix": cm.tolist(),
        "report": report,
    }


def pretty_print_metrics(metrics: Dict[str, object]) -> None:
    """طباعة المقاييس بشكل منسق."""
    labels = metrics.get("labels", [])
    cm = np.array(metrics.get("confusion_matrix", []))
    acc = metrics.get("accuracy", 0.0)
    logger.info("Accuracy: %.3f", acc)
    logger.info("Labels: %s", labels)
    logger.info("Confusion Matrix:\n%s", cm)
