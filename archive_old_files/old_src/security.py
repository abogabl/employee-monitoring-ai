"""
SecurityManager: تطبيق إجراءات أمان وخصوصية أساسية.
- تشفير/فك تشفير بيانات حساسة (ملفات/بيانات خام)
- تجزئة كلمات المرور والتحقق منها (bcrypt)
- مفاتيح API بسيطة وتحققها
- سجل تدقيق للوصول والتغييرات
"""
from __future__ import annotations

import base64
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import bcrypt
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


@dataclass
class SecurityConfig:
    encryption_enabled: bool = True
    key_file: str = "keys/encryption.key"


class SecurityManager:
    def __init__(self, config_path: str | Path = "config/security_config.json") -> None:
        self.config_path = Path(config_path)
        self.cfg = self._load_config()
        self.key = self._load_or_create_key(self.cfg.key_file)
        self.fernet = Fernet(self.key)
        self.api_keys_file = Path("keys/api_keys.json")
        self.api_keys_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.api_keys_file.exists():
            self.api_keys_file.write_text("{}", encoding="utf-8")
        self.audit_log = Path("logs/audit.log")
        self.audit_log.parent.mkdir(parents=True, exist_ok=True)

    # ---------------- Config/Keys ----------------
    def _load_config(self) -> SecurityConfig:
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            enc = data.get("encryption", {})
            return SecurityConfig(encryption_enabled=bool(enc.get("enabled", True)), key_file=enc.get("key_file", "keys/encryption.key"))
        except Exception:
            return SecurityConfig()

    def _load_or_create_key(self, key_file: str) -> bytes:
        p = Path(key_file)
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists():
            return p.read_bytes()
        key = Fernet.generate_key()
        p.write_bytes(key)
        return key

    # ---------------- Encryption ----------------
    def encrypt_data(self, data: bytes, key: bytes | None = None) -> bytes:
        if key is None:
            key = self.key
        f = Fernet(key)
        return f.encrypt(data)

    def decrypt_data(self, encrypted: bytes, key: bytes | None = None) -> bytes:
        if key is None:
            key = self.key
        f = Fernet(key)
        return f.decrypt(encrypted)

    # ---------------- Passwords ----------------
    def hash_password(self, password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def verify_password(self, password: str, pw_hash: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), pw_hash.encode("utf-8"))
        except Exception:
            return False

    # ---------------- API Keys ----------------
    def generate_api_key(self) -> str:
        # 32 bytes random -> urlsafe base64
        key = base64.urlsafe_b64encode(os.urandom(32)).decode("ascii").rstrip("=")
        data = json.loads(self.api_keys_file.read_text(encoding="utf-8"))
        data[key] = {"created_at": datetime.utcnow().isoformat(), "active": True}
        self.api_keys_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return key

    def verify_api_key(self, key: str) -> bool:
        try:
            data = json.loads(self.api_keys_file.read_text(encoding="utf-8"))
            rec = data.get(key)
            return bool(rec and rec.get("active", False))
        except Exception:
            return False

    # ---------------- Audit ----------------
    def log_access(self, user: str, resource: str, action: str, ip: str = "-") -> None:
        ts = datetime.utcnow().isoformat()
        line = f"{ts}\t{ip}\t{user}\t{action}\t{resource}\n"
        try:
            with self.audit_log.open("a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass
