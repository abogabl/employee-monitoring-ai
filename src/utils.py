"""
دوال مساعدة لمعالجة الصور والصناديق.
توفر: IoU، حساب مركز الصندوق، قص صورة الشخص، تغيير الحجم مع الحفاظ على النسبة، ورسم نص بخلفية.
"""
from __future__ import annotations

import cv2
import numpy as np
from typing import Tuple


def calculate_iou(box1: Tuple[int, int, int, int], box2: Tuple[int, int, int, int]) -> float:
    """حساب تقاطع على اتحاد IoU بين صندوقين [x1, y1, x2, y2]."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter_w = max(0, x2 - x1 + 1)
    inter_h = max(0, y2 - y1 + 1)
    inter = inter_w * inter_h

    area1 = (box1[2] - box1[0] + 1) * (box1[3] - box1[1] + 1)
    area2 = (box2[2] - box2[0] + 1) * (box2[3] - box2[1] + 1)

    union = max(area1 + area2 - inter, 1)
    return float(inter / union)


def calculate_centroid(box: Tuple[int, int, int, int]) -> Tuple[int, int]:
    """حساب مركز الصندوق (x, y)."""
    x1, y1, x2, y2 = box
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    return cx, cy


def crop_person(frame: np.ndarray, box: Tuple[int, int, int, int], padding: int = 10) -> np.ndarray:
    """قص صورة الشخص من الإطار مع هامش padding آمن داخل حدود الصورة."""
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = box
    x1 = max(0, x1 - padding)
    y1 = max(0, y1 - padding)
    x2 = min(w - 1, x2 + padding)
    y2 = min(h - 1, y2 + padding)
    return frame[y1 : y2 + 1, x1 : x2 + 1].copy()


def resize_with_aspect_ratio(image: np.ndarray, target_size: Tuple[int, int]) -> np.ndarray:
    """تغيير الحجم مع الحفاظ على النسبة aspect ratio بإضافة أشرطة سوداء إذا لزم."""
    target_w, target_h = target_size
    h, w = image.shape[:2]
    if h == 0 or w == 0:
        return np.zeros((target_h, target_w, 3), dtype=image.dtype)

    scale = min(target_w / w, target_h / h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

    canvas = np.zeros((target_h, target_w, 3), dtype=image.dtype)
    x_offset = (target_w - new_w) // 2
    y_offset = (target_h - new_h) // 2
    canvas[y_offset : y_offset + new_h, x_offset : x_offset + new_w] = resized
    return canvas


def draw_text_with_background(
    frame: np.ndarray,
    text: str,
    position: Tuple[int, int],
    color: Tuple[int, int, int] = (0, 255, 0),
    font_scale: float = 0.5,
    thickness: int = 1,
) -> np.ndarray:
    """رسم نص مع خلفية سوداء نصف شفافة لتحسين القراءة."""
    x, y = position
    font = cv2.FONT_HERSHEY_SIMPLEX

    (tw, th), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    # مستطيل الخلفية
    bg_tl = (x, y - th - baseline - 4)
    bg_br = (x + tw + 4, y + 2)
    cv2.rectangle(frame, bg_tl, bg_br, (0, 0, 0), -1)
    # النص
    cv2.putText(frame, text, (x + 2, y - 2), font, font_scale, color, thickness, cv2.LINE_AA)
    return frame
