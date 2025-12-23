"""
PrivacyManager: أدوات خصوصية وحماية بيانات.
- إخفاء الهوية عبر طمس الوجوه في الفيديوهات المحفوظة
- سياسة الاحتفاظ بالبيانات (حذف قديم)
- تصدير/حذف بيانات شخصية حسب المعرف
"""
from __future__ import annotations

import io
import logging
import shutil
import sqlite3
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import cv2

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


@dataclass
class RetentionPolicy:
    attendance_logs: int = 365
    video_recordings: int = 30
    reports: int = 180
    audit_logs: int = 730


class PrivacyManager:
    def __init__(self, project_root: str | Path = ".", security_config: str | Path = "config/security_config.json") -> None:
        self.root = Path(project_root).resolve()
        self.config_path = Path(security_config)
        self.policy = self._load_policy()
        # كاشف وجوه بسيط من OpenCV (Haar)
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    def _load_policy(self) -> RetentionPolicy:
        try:
            import json
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            rp = data.get("data_retention", {})
            return RetentionPolicy(
                attendance_logs=int(rp.get("attendance_logs", 365)),
                video_recordings=int(rp.get("video_recordings", 30)),
                reports=int(rp.get("reports", 180)),
                audit_logs=int(rp.get("audit_logs", 730)),
            )
        except Exception:
            return RetentionPolicy()

    # ---------------- Anonymization ----------------
    def anonymize_video(self, video_path: str | Path, blur_strength: int = 35) -> str:
        p = Path(video_path)
        if not p.exists():
            raise FileNotFoundError(str(p))
        cap = cv2.VideoCapture(str(p))
        if not cap.isOpened():
            raise RuntimeError("تعذر فتح الفيديو")
        out_path = p.with_name(p.stem + "_anon" + p.suffix)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        writer = cv2.VideoWriter(str(out_path), fourcc, fps, (w, h))
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, 1.1, 5)
                for (x, y, fw, fh) in faces:
                    roi = frame[y:y+fh, x:x+fw]
                    k = max(3, blur_strength | 1)
                    roi = cv2.GaussianBlur(roi, (k, k), 0)
                    frame[y:y+fh, x:x+fw] = roi
                writer.write(frame)
        finally:
            cap.release()
            writer.release()
        logger.info("تم إنشاء فيديو مخفي الهوية: %s", out_path)
        return str(out_path)

    # ---------------- Personal Data Ops ----------------
    def delete_personal_data(self, employee_id: str) -> None:
        # حذف صور الوجوه
        faces_dir = self.root / "employees_database" / "faces" / employee_id
        if faces_dir.exists():
            shutil.rmtree(faces_dir, ignore_errors=True)
        # حذف سجلات الحضور
        db_path = self.root / "attendance_db" / "attendance.db"
        if db_path.exists():
            try:
                con = sqlite3.connect(str(db_path))
                cur = con.cursor()
                cur.execute("DELETE FROM attendance_logs WHERE employee_id=?", (employee_id,))
                con.commit()
                con.close()
            except Exception as e:
                logger.warning("فشل حذف سجلات الحضور: %s", e)
        logger.info("تم حذف بيانات الموظف %s", employee_id)

    def export_personal_data(self, employee_id: str) -> str:
        # تجميع بيانات الموظف في ZIP
        out = self.root / "reports" / f"personal_data_{employee_id}.zip"
        out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
            # معلومات الموظف
            emp_json = self.root / "employees_database" / "employees.json"
            if emp_json.exists():
                z.write(emp_json, arcname="employees.json")
            # صور الوجوه
            faces_dir = self.root / "employees_database" / "faces" / employee_id
            if faces_dir.exists():
                for f in faces_dir.glob("**/*"):
                    if f.is_file():
                        z.write(f, arcname=str(Path("faces") / employee_id / f.name))
            # سجلات الحضور (CSV مستخرج)
            db_path = self.root / "attendance_db" / "attendance.db"
            if db_path.exists():
                try:
                    con = sqlite3.connect(str(db_path))
                    cur = con.cursor()
                    import csv
                    from io import StringIO
                    cur.execute("SELECT * FROM attendance_logs WHERE employee_id=?", (employee_id,))
                    rows = cur.fetchall()
                    if rows:
                        headers = [d[0] for d in cur.description]
                        sio = StringIO()
                        w = csv.writer(sio)
                        w.writerow(headers)
                        w.writerows(rows)
                        z.writestr(f"attendance_{employee_id}.csv", sio.getvalue())
                    con.close()
                except Exception as e:
                    logger.warning("فشل تصدير سجلات الحضور: %s", e)
        logger.info("تم تصدير البيانات الشخصية إلى: %s", out)
        return str(out)

    # ---------------- Retention ----------------
    def apply_retention_policy(self) -> Dict[str, int]:
        removed = {"videos": 0, "reports": 0, "audit": 0}
        now = datetime.now()
        # فيديوهات
        vids = self.root / "videos"
        if vids.exists():
            cutoff = now - timedelta(days=self.policy.video_recordings)
            for f in vids.glob("**/*"):
                if f.is_file() and datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                    f.unlink(missing_ok=True)
                    removed["videos"] += 1
        # تقارير
        reps = self.root / "reports"
        if reps.exists():
            cutoff = now - timedelta(days=self.policy.reports)
            for f in reps.glob("**/*"):
                if f.is_file() and datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                    f.unlink(missing_ok=True)
                    removed["reports"] += 1
        # سجلات تدقيق
        logs = self.root / "logs"
        if logs.exists():
            cutoff = now - timedelta(days=self.policy.audit_logs)
            for f in logs.glob("**/*"):
                if f.is_file() and datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                    f.unlink(missing_ok=True)
                    removed["audit"] += 1
        logger.info("تم تطبيق سياسة الاحتفاظ: %s", removed)
        return removed
