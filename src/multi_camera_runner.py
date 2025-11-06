"""
MultiCameraRunner: إدارة عدة كاميرات بالتوازي عبر عمليات فرعية مستقلة.
- تحميل و验证 إعدادات الكاميرات من config/cameras_config.json
- تشغيل/إيقاف/إعادة تشغيل عملية لكل كاميرا (باستدعاء main_production.py)
- مراقبة الحالة وإعادة التشغيل التلقائي
- دمج تقارير اليوم من جميع الكاميرات
ملاحظة: لاستخدام استقرار أفضل على Windows، نستخدم subprocess بدل multiprocessing المباشر.
"""
from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .camera_health_monitor import CameraHealthMonitor

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


CONFIG_DEFAULT = "config/cameras_config.json"


@dataclass
class CameraProcess:
    camera_id: str
    cfg: Dict[str, object]
    process: Optional[subprocess.Popen] = None
    start_time: float = field(default_factory=lambda: time.time())
    last_heartbeat: Optional[float] = None
    restart_count: int = 0
    last_error: str = ""


class MultiCameraRunner:
    def __init__(self, config_path: str | Path = CONFIG_DEFAULT) -> None:
        self.config_path = Path(config_path)
        self.config: Dict[str, object] = {}
        self.cameras: Dict[str, CameraProcess] = {}
        self.health = CameraHealthMonitor()
        self.output_dir = Path("results")

    # ---------------- Config ----------------
    def load_config(self) -> Dict[str, object]:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config not found: {self.config_path}")
        self.config = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.output_dir = Path(self.config.get("global_settings", {}).get("output_dir", "results/"))  # type: ignore[index]
        return self.config

    def validate_config(self) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        gs = self.config.get("global_settings", {}) if isinstance(self.config, dict) else {}
        if "cameras" not in self.config:
            errors.append("'cameras' missing in config")
            return False, errors
        cams = self.config["cameras"]  # type: ignore[index]
        if not isinstance(cams, list) or not cams:
            errors.append("'cameras' must be a non-empty list")
        seen_ids = set()
        for c in cams:
            cid = str(c.get("id", ""))
            if not cid:
                errors.append("camera missing id")
                continue
            if cid in seen_ids:
                errors.append(f"duplicate camera id: {cid}")
            seen_ids.add(cid)
            if not c.get("source"):
                errors.append(f"camera {cid} missing source")
            if c.get("enabled") not in (True, False):
                errors.append(f"camera {cid} missing enabled flag")
        return len(errors) == 0, errors

    # ---------------- Process Control ----------------
    def _build_command(self, cam_cfg: Dict[str, object]) -> List[str]:
        # تشغيل main_production.py مع معلمات الكاميرا المحددة
        py = sys.executable or "python"
        script = str((Path(__file__).parent / "main_production.py").resolve())
        source = str(cam_cfg.get("source", "0"))
        camera_id = str(cam_cfg.get("id", "cam"))
        device = str(cam_cfg.get("device", "cpu"))
        imgsz = str(cam_cfg.get("imgsz", 640))
        conf = str(cam_cfg.get("conf", 0.5))
        gs = self.config.get("global_settings", {}) if isinstance(self.config, dict) else {}
        args = [
            py,
            script,
            "--source", source,
            "--camera-id", camera_id,
            "--device", device if device in ("cpu", "cuda") else ("cuda" if device.startswith("cuda") else "cpu"),
            "--imgsz", imgsz,
            "--conf", conf,
            "--report-interval", str(gs.get("report_interval", 300)),
        ]
        if gs.get("enable_face_recognition", True):
            args.append("--enable-face-recognition")
        if gs.get("enable_activity_recognition", True):
            args.append("--enable-activity-recognition")
        if gs.get("enable_attendance", True):
            args.append("--enable-attendance")
        # إخراج الفيديو لكل كاميرا
        out_dir = Path(gs.get("output_dir", "results/"))  # type: ignore[arg-type]
        out_dir.mkdir(parents=True, exist_ok=True)
        out_video = out_dir / f"{camera_id}_output.mp4"
        args += ["--output-video", str(out_video)]
        return args

    def start_camera(self, cam_cfg: Dict[str, object]) -> CameraProcess:
        cid = str(cam_cfg.get("id"))
        proc_info = CameraProcess(camera_id=cid, cfg=cam_cfg)
        # فحص الاتصال قبل التشغيل
        self.health.check_camera_connection(cid, str(cam_cfg.get("source", "0")))
        cmd = self._build_command(cam_cfg)
        env = os.environ.copy()
        # يمكن لاحقاً تمرير متغيرات بيئة لمسارات DB خاصة لكل كاميرا
        try:
            logger.info("تشغيل الكاميرا %s: %s", cid, " ".join(cmd))
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            proc_info.process = p
            self.cameras[cid] = proc_info
            return proc_info
        except Exception as e:
            logger.exception("فشل تشغيل الكاميرا %s: %s", cid, e)
            proc_info.last_error = str(e)
            self.cameras[cid] = proc_info
            return proc_info

    def stop_camera(self, camera_id: str) -> None:
        cp = self.cameras.get(camera_id)
        if not cp or not cp.process:
            return
        try:
            logger.info("إيقاف الكاميرا %s", camera_id)
            cp.process.terminate()
            try:
                cp.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                cp.process.kill()
        except Exception:
            pass

    def restart_camera(self, camera_id: str) -> None:
        cfg = self.cameras.get(camera_id).cfg if self.cameras.get(camera_id) else None  # type: ignore[assignment]
        self.stop_camera(camera_id)
        time.sleep(1)
        if cfg:
            info = self.start_camera(cfg)
            info.restart_count += 1

    def start_all_cameras(self, only_ids: Optional[List[str]] = None) -> None:
        self.load_config()
        ok, errs = self.validate_config()
        if not ok:
            raise ValueError("Config validation errors: " + "; ".join(errs))
        for cam in sorted(self.config["cameras"], key=lambda c: c.get("priority", 999)):  # type: ignore[index]
            if not cam.get("enabled", True):
                continue
            if only_ids and cam.get("id") not in only_ids:
                continue
            self.start_camera(cam)

    def stop_all_cameras(self) -> None:
        for cid in list(self.cameras.keys()):
            self.stop_camera(cid)

    # ---------------- Status/Reports ----------------
    def get_camera_status(self, camera_id: str) -> Dict[str, object]:
        cp = self.cameras.get(camera_id)
        st = self.health.status.get(camera_id)
        proc_alive = (cp.process.poll() is None) if (cp and cp.process) else False  # type: ignore[union-attr]
        return {
            "camera_id": camera_id,
            "running": proc_alive,
            "restart_count": cp.restart_count if cp else 0,
            "last_error": cp.last_error if cp else "",
            "health": {
                "ok": st.ok if st else False,
                "frozen": st.frozen if st else False,
                "fps": st.fps if st else None,
                "errors": st.error_count if st else 0,
                "message": st.message if st else "",
            },
        }

    def get_all_status(self) -> Dict[str, Dict[str, object]]:
        return {cid: self.get_camera_status(cid) for cid in self.cameras.keys()}

    def merge_reports(self, d: date | str) -> pd.DataFrame:
        d_str = d if isinstance(d, str) else d.isoformat()
        reports_dir = Path("reports")
        files = list(reports_dir.glob(f"daily_{d_str}.csv"))
        if not files:
            return pd.DataFrame()
        frames = []
        for f in files:
            try:
                frames.append(pd.read_csv(f))
            except Exception:
                pass
        if not frames:
            return pd.DataFrame()
        df = pd.concat(frames, ignore_index=True)
        return df

    # ---------------- Monitor loop (optional) ----------------
    def monitor_loop(self, interval: float = 5.0) -> None:
        """مراقبة دورية لإعادة التشغيل عند التعطل وفحص التجمّد."""
        try:
            while True:
                for cid, cp in list(self.cameras.items()):
                    p = cp.process
                    if p and (p.poll() is not None):
                        logger.warning("الكاميرا %s: العملية توقفت، سيتم إعادة التشغيل.", cid)
                        self.restart_camera(cid)
                    # فحص اتصال المصدر بشكل دوري
                    src = str(cp.cfg.get("source", "0"))
                    self.health.check_camera_connection(cid, src)
                    # كشف تجمّد عبر heartbeat إذا توفر
                    self.health.detect_frozen_camera(cid, cp.last_heartbeat, timeout_seconds=15)
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("خروج من حلقة المراقبة")
