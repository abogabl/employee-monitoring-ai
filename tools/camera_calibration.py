"""
معايرة الكاميرا باستخدام صور لوحة الشطرنج.
مثال:
python camera_calibration.py --source cam1 --calibration-images calibration/*.jpg
الناتج: camera_matrix, distortion_coefficients محفوظة في ملف JSON.
"""
from __future__ import annotations

import argparse
import glob
import json
import logging
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("camera_calibration")


def calibrate(images: List[str], pattern_size: Tuple[int, int] = (9, 6), square_size: float = 1.0):
    objp = np.zeros((pattern_size[0] * pattern_size[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:pattern_size[0], 0:pattern_size[1]].T.reshape(-1, 2)
    objp *= square_size

    objpoints = []
    imgpoints = []

    for fname in images:
        img = cv2.imread(fname)
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ret, corners = cv2.findChessboardCorners(gray, pattern_size, None)
        if ret:
            corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), (cv2.TermCriteria_EPS + cv2.TermCriteria_MAX_ITER, 30, 0.001))
            objpoints.append(objp)
            imgpoints.append(corners2)

    if not objpoints:
        raise RuntimeError("لم يتم العثور على نمط الشطرنج في أي صورة")

    ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)
    return ret, mtx, dist


def main() -> None:
    ap = argparse.ArgumentParser(description="معايرة الكاميرا")
    ap.add_argument("--source", required=True, help="معرّف الكاميرا (يُستخدم في اسم الملف الناتج)")
    ap.add_argument("--calibration-images", required=True, help="نمط glob لصور المعايرة")
    ap.add_argument("--pattern", default="9x6", help="عدد نقاط الشطرنج (أعمدةxصفوف)")
    ap.add_argument("--square-size", type=float, default=1.0, help="حجم المربع بوحدتك")
    args = ap.parse_args()

    cols, rows = [int(x) for x in args.pattern.lower().split("x")]
    images = sorted(glob.glob(args.calibration_images))
    if not images:
        logger.error("لا توجد صور مطابقة للنمط")
        return

    ret, mtx, dist = calibrate(images, (cols, rows), args.square_size)
    out = Path("config") / f"camera_{args.source}_calibration.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "rms": ret,
        "camera_matrix": mtx.tolist(),
        "dist_coeffs": dist.tolist()
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("تم حفظ المعايرة في %s", out)


if __name__ == "__main__":
    main()
