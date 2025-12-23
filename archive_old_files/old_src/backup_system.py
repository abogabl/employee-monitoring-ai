"""
BackupSystem: نسخ احتياطي آلي وقابل للاستعادة للمكوّنات الرئيسة.
- يدعم full / incremental / differential
- ضغط إلى ZIP
- رفع اختياري للخدمات السحابية (placeholder)
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


@dataclass
class BackupEntry:
    rel_path: str
    size: int
    mtime: float
    sha1: str


class BackupSystem:
    """مدير النسخ الاحتياطي.

    المسارات الافتراضية:
    - attendance_db/attendance.db
    - employees_database/employees.json
    - models/face_encodings.pkl
    - config/*.json
    - reports/*.csv, *.xlsx (المهمة)
    """

    def __init__(self, root: str | Path = ".", backups_dir: str | Path = "backups") -> None:
        self.root = Path(root).resolve()
        self.backups_dir = (self.root / backups_dir).resolve()
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        self.catalog_path = self.backups_dir / "backup_catalog.json"
        self._catalog: Dict[str, dict] = self._load_catalog()

    # ---------------- Catalog helpers ----------------
    def _load_catalog(self) -> Dict[str, dict]:
        if self.catalog_path.exists():
            try:
                return json.loads(self.catalog_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_catalog(self) -> None:
        try:
            self.catalog_path.write_text(json.dumps(self._catalog, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("فشل حفظ الكاتالوج: %s", e)

    # ---------------- File selection ----------------
    def _gather_files(self) -> List[Path]:
        files: List[Path] = []
        add = files.append
        # قواعد ثابتة
        for p in [self.root / "attendance_db" / "attendance.db",
                  self.root / "employees_database" / "employees.json",
                  self.root / "models" / "face_encodings.pkl"]:
            if p.exists():
                add(p)
        # إعدادات
        cfg_dir = self.root / "config"
        if cfg_dir.exists():
            for p in cfg_dir.glob("*.json"):
                add(p)
        # تقارير
        rep_dir = self.root / "reports"
        if rep_dir.exists():
            for p in rep_dir.glob("*.*"):
                if p.suffix.lower() in {".csv", ".xlsx", ".xls"}:
                    add(p)
        return files

    # ---------------- Hashing ----------------
    def _sha1(self, path: Path, block: int = 1024 * 1024) -> str:
        h = hashlib.sha1()
        with path.open("rb") as f:
            while True:
                b = f.read(block)
                if not b:
                    break
                h.update(b)
        return h.hexdigest()

    def _manifest(self, paths: List[Path]) -> Dict[str, BackupEntry]:
        man: Dict[str, BackupEntry] = {}
        for p in paths:
            try:
                st = p.stat()
                rel = str(p.relative_to(self.root))
                man[rel] = BackupEntry(rel_path=rel, size=st.st_size, mtime=st.st_mtime, sha1=self._sha1(p))
            except Exception:
                continue
        return man

    # ---------------- Create backups ----------------
    def create_backup(self, backup_type: str = "full") -> str:
        """إنشاء نسخة احتياطية: full أو incremental أو differential. يرجع مسار المجلد الناتج."""
        backup_type = backup_type.lower()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = self.backups_dir / f"{ts}_{backup_type}"
        out_dir.mkdir(parents=True, exist_ok=True)

        paths = self._gather_files()
        man = self._manifest(paths)

        base_manifest: Dict[str, dict] = {}
        if backup_type in {"incremental", "differential"}:
            # ابحث عن آخر full (لـ differential) أو آخر أي نسخة (لـ incremental)
            prev_key = None
            if backup_type == "differential":
                # آخر full
                for k in sorted(self._catalog.keys(), reverse=True):
                    if self._catalog[k].get("type") == "full":
                        prev_key = k
                        break
            else:
                # آخر أي
                if self._catalog:
                    prev_key = sorted(self._catalog.keys(), reverse=True)[0]
            if prev_key:
                base_manifest = self._catalog[prev_key].get("manifest", {})

        copied = 0
        for rel, entry in man.items():
            # قرر النسخ
            need_copy = True
            if base_manifest:
                prev = base_manifest.get(rel)
                if prev and prev.get("sha1") == entry.sha1:
                    if backup_type in {"incremental", "differential"}:
                        need_copy = False
            if need_copy:
                src = self.root / rel
                dst = out_dir / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(src, dst)
                    copied += 1
                except Exception as e:
                    logger.warning("فشل نسخ %s: %s", src, e)

        meta = {
            "timestamp": ts,
            "type": backup_type,
            "copied_files": copied,
            "manifest": {k: vars(v) for k, v in man.items()},
        }
        (out_dir / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        # تحديث الكاتالوج
        self._catalog[ts] = {"type": backup_type, "manifest": meta["manifest"]}
        self._save_catalog()
        logger.info("تم إنشاء نسخة احتياطية: %s (ملفات منسوخة=%d)", out_dir, copied)
        return str(out_dir)

    def compress_backup(self, backup_path: str | Path) -> str:
        p = Path(backup_path)
        zip_path = str(p) + ".zip"
        shutil.make_archive(str(p), "zip", root_dir=str(p))
        logger.info("تم ضغط النسخة: %s", zip_path)
        return zip_path

    def upload_to_cloud(self, backup_path: str | Path, service: str = "s3") -> bool:
        # Placeholder: يمكن لاحقاً دمج boto3 لـ S3 أو غيره.
        logger.info("[CLOUD] رفع %s إلى %s (غير مفعل فعلياً)", backup_path, service)
        return False

    def list_backups(self) -> List[Dict[str, str]]:
        res: List[Dict[str, str]] = []
        for d in sorted(self.backups_dir.glob("*_*")):
            if d.is_dir():
                meta = d / "metadata.json"
                typ = "?"
                if meta.exists():
                    try:
                        typ = json.loads(meta.read_text(encoding="utf-8")).get("type", "?")
                    except Exception:
                        pass
                res.append({"path": str(d), "type": typ})
        return res

    def delete_old_backups(self, keep_days: int = 30) -> int:
        cutoff = time.time() - keep_days * 86400
        removed = 0
        for d in self.backups_dir.glob("*_*"):
            if not d.is_dir():
                continue
            try:
                ts = datetime.strptime(d.name.split("_", 1)[0], "%Y%m%d")
                if ts.timestamp() < cutoff:
                    shutil.rmtree(d, ignore_errors=True)
                    removed += 1
            except Exception:
                continue
        logger.info("تم حذف %d نسخ قديمة", removed)
        return removed

    def restore_backup(self, backup_path: str | Path) -> bool:
        p = Path(backup_path)
        if p.suffix.lower() == ".zip" and p.exists():
            # فك الضغط إلى مجلد مؤقت ثم المتابعة
            logger.warning("سيتم فك الضغط يدوياً قبل الاستعادة")
            return False
        if not p.exists() or not p.is_dir():
            logger.error("مسار النسخة غير صالح: %s", p)
            return False
        # نسخ الملفات على الأصل بحذر (لاستعادة كاملة)
        for f in p.rglob('*'):
            if f.is_file() and f.name != "metadata.json":
                rel = f.relative_to(p)
                dst = self.root / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(f, dst)
                except Exception as e:
                    logger.warning("فشل الاستعادة %s: %s", f, e)
        logger.info("اكتملت الاستعادة من %s", p)
        return True

    # ---------------- Scheduling (placeholder) ----------------
    def schedule_backup(self, frequency: str = "daily", time_str: str = "23:00") -> None:
        """تحديد جدولة من داخل التطبيق (مقترحة للاستخدام مع جدولة خارجية كـ Task Scheduler)."""
        logger.info("الرجاء استخدام Task Scheduler/cron لتشغيل create_backup دوريًا (%s @ %s)", frequency, time_str)
