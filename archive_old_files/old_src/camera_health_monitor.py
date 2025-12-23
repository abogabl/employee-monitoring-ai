"""
CameraHealthMonitor: مراقبة صحة الكاميرات والعمليات المرتبطة بها.
- يفحص الاتصال بالمصدر (فتح/قراءة إطار اختبار)
- يتتبع FPS تقديري (اختياري إن وُجدت بيانات من العملية)
- يرصد السقوط/التجمّد بناءً على أحدث heartbeat (إن توفر)
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

import cv2

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


@dataclass
class CameraStatus:
    camera_id: str
    ok: bool = False
    last_check: float = field(default_factory=lambda: time.time())
    fps: Optional[float] = None
    frame_drops: int = 0
    frozen: bool = False
    error_count: int = 0
    message: str = ""


class CameraHealthMonitor:
    """مراقب صحة للكاميرات يعتمد على فحوصات دورية خفيفة الوزن."""

    def __init__(self) -> None:
        self.status: Dict[str, CameraStatus] = {}

    def _open_probe(self, source: str) -> bool:
        try:
            cap = cv2.VideoCapture(int(source)) if source.isdigit() else cv2.VideoCapture(source)
            if not cap.isOpened():
                return False
            ok, _ = cap.read()
            cap.release()
            return bool(ok)
        except Exception:
            return False

    def check_camera_connection(self, camera_id: str, source: str) -> bool:
        ok = self._open_probe(source)
        st = self.status.get(camera_id) or CameraStatus(camera_id=camera_id)
        st.ok = ok
        st.last_check = time.time()
        st.message = "OK" if ok else "Cannot open source"
        self.status[camera_id] = st
        return ok

    def get_fps(self, camera_id: str) -> float:
        st = self.status.get(camera_id)
        return float(st.fps or 0.0) if st else 0.0

    def get_frame_drops(self, camera_id: str) -> int:
        st = self.status.get(camera_id)
        return int(st.frame_drops or 0) if st else 0

    def detect_frozen_camera(self, camera_id: str, heartbeat_ts: Optional[float], timeout_seconds: float = 10.0) -> bool:
        now = time.time()
        if heartbeat_ts is None:
            return False
        frozen = (now - heartbeat_ts) > timeout_seconds
        st = self.status.get(camera_id) or CameraStatus(camera_id=camera_id)
        st.frozen = frozen
        st.last_check = now
        st.message = "Frozen" if frozen else st.message
        self.status[camera_id] = st
        return frozen

    def get_error_count(self, camera_id: str) -> int:
        st = self.status.get(camera_id)
        return int(st.error_count or 0) if st else 0

    def inc_error(self, camera_id: str) -> None:
        st = self.status.get(camera_id) or CameraStatus(camera_id=camera_id)
        st.error_count += 1
        self.status[camera_id] = st

    def send_alert(self, camera_id: str, issue: str) -> None:
        logger.warning("[ALERT][%s] %s", camera_id, issue)
