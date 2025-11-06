"""
تكبير بيانات الوجوه عبر عمليات شائعة.
مثال:
python data_augmentation.py --input faces/ --output augmented/ --operations flip,rotate,brightness,blur --multiplier 5
"""
from __future__ import annotations

import argparse
import logging
import random
from pathlib import Path

import cv2
import numpy as np
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("data_augmentation")


def aug_flip(img: np.ndarray) -> np.ndarray:
    return cv2.flip(img, 1)


def aug_rotate(img: np.ndarray, angle: float = None) -> np.ndarray:
    h, w = img.shape[:2]
    if angle is None:
        angle = random.uniform(-15, 15)
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def aug_brightness(img: np.ndarray) -> np.ndarray:
    alpha = random.uniform(0.7, 1.3)
    beta = random.randint(-20, 20)
    out = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)
    return out


def aug_blur(img: np.ndarray) -> np.ndarray:
    k = random.choice([3, 5])
    return cv2.GaussianBlur(img, (k, k), 0)


def aug_noise(img: np.ndarray) -> np.ndarray:
    noise = np.random.normal(0, 10, img.shape).astype(np.int16)
    out = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return out


def aug_color_jitter(img: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] *= random.uniform(0.8, 1.2)
    hsv[..., 2] *= random.uniform(0.8, 1.2)
    hsv = np.clip(hsv, 0, 255).astype(np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


OPS = {
    "flip": aug_flip,
    "rotate": aug_rotate,
    "brightness": aug_brightness,
    "blur": aug_blur,
    "noise": aug_noise,
    "color": aug_color_jitter,
}


def main() -> None:
    ap = argparse.ArgumentParser(description="تكبير البيانات")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--operations", default="flip,rotate,brightness,blur")
    ap.add_argument("--multiplier", type=int, default=5)
    args = ap.parse_args()

    src = Path(args.input)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    ops = [o.strip() for o in args.operations.split(",") if o.strip()]

    images = [p for p in src.glob("**/*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    pbar = tqdm(images, desc="Augmenting")
    for img_path in pbar:
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        for i in range(args.multiplier):
            aug = img.copy()
            for op in ops:
                fn = OPS.get(op)
                if fn:
                    aug = fn(aug)
            out_name = out / f"{img_path.stem}_aug_{i}{img_path.suffix}"
            cv2.imwrite(str(out_name), aug)
    logger.info("اكتملت عملية التكبير")


if __name__ == "__main__":
    main()
