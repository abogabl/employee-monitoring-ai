"""
عرض معلومات النظام والبيئة.
مثال:
python system_info.py
"""
from __future__ import annotations

import importlib
import json
import platform
import shutil
from pathlib import Path

import psutil

try:
    import torch  # type: ignore
except Exception:
    torch = None  # type: ignore

try:
    import cv2  # type: ignore
except Exception:
    cv2 = None  # type: ignore

LIBS = [
    "numpy",
    "pandas",
    "ultralytics",
    "insightface",
    "onnxruntime",
    "mediapipe",
    "tqdm",
]


def get_versions():
    out = {}
    for lib in LIBS:
        try:
            m = importlib.import_module(lib)
            ver = getattr(m, "__version__", "?")
            out[lib] = ver
        except Exception:
            out[lib] = "not installed"
    return out


def main() -> None:
    info = {
        "os": platform.platform(),
        "python": platform.python_version(),
        "cuda_available": bool(torch and getattr(torch, "cuda", None) and torch.cuda.is_available()),
        "gpu_name": torch.cuda.get_device_name(0) if (torch and torch.cuda.is_available()) else None,
        "ram_gb": round(psutil.virtual_memory().total / (1024 ** 3), 1),
        "disk_free_gb": round(shutil.disk_usage(Path(".")).free / (1024 ** 3), 1),
        "opencv": cv2.__version__ if cv2 else None,
        "libraries": get_versions(),
        "models_present": {
            "yolov8n": Path("yolov8n.pt").exists(),
            "encodings": Path("models/face_encodings.pkl").exists(),
        },
    }
    print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
