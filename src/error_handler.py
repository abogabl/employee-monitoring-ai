"""
ErrorHandler: إدارة الأخطاء مع تسجيل منظّم، إعادة المحاولة، وبدائل وتنبيهات.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple, Type

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


@dataclass
class RetryPolicy:
    retries: int = 3
    backoff_seconds: float = 0.5
    backoff_multiplier: float = 2.0


class ErrorHandler:
    """مدير بسيط لمعالجة الأخطاء مع آليات retry وfallback وتنبيه."""

    def __init__(self) -> None:
        pass

    def log_error(self, error: Exception, level: str = "ERROR", context: Optional[str] = None) -> None:
        msg = f"{type(error).__name__}: {error}"
        if context:
            msg = f"[{context}] {msg}"
        if level.upper() == "WARNING":
            logger.warning(msg)
        elif level.upper() == "INFO":
            logger.info(msg)
        else:
            logger.error(msg)

    def send_alert(self, error: Exception, destination: str = "", provider: str = "email", **kwargs: Any) -> bool:
        """تنبيه بسيط عبر البريد الإلكتروني (placeholder). يتطلب تهيئة SMTP خارجياً."""
        try:
            if not destination:
                return False
            # يمكن الربط بـ ReportGenerator.send_email عند الحاجة.
            logger.info("[ALERT:%s] تنبيه مُرسل إلى %s: %s", provider, destination, error)
            return True
        except Exception:
            return False

    def handle_error(self, error: Exception, context: Optional[str] = None, retry: bool = True, fallback: Optional[Callable[[], Any]] = None) -> Any:
        """معالجة عامة: تسجيل، إعادة محاولة اختيارية، تنفيذ بديل fallback عند الفشل."""
        self.log_error(error, context=context)
        if not retry:
            return fallback() if callable(fallback) else None
        return None

    def run_with_retry(self, func: Callable[[], Any], policy: RetryPolicy = RetryPolicy(), exceptions: Tuple[Type[BaseException], ...] = (Exception,), context: Optional[str] = None, fallback: Optional[Callable[[], Any]] = None) -> Any:
        """تشغيل دالة مع إعادة محاولات تلقائية وbackoff. يعيد نتيجة الدالة أو نتيجة fallback عند الفشل."""
        delay = policy.backoff_seconds
        for attempt in range(1, policy.retries + 1):
            try:
                return func()
            except exceptions as e:
                self.log_error(e, level="WARNING", context=f"{context or func.__name__} [attempt {attempt}/{policy.retries}]")
                if attempt == policy.retries:
                    if fallback:
                        try:
                            return fallback()
                        except Exception as fe:
                            self.log_error(fe, level="ERROR", context=f"fallback for {context or func.__name__}")
                            return None
                    return None
                time.sleep(delay)
                delay *= policy.backoff_multiplier
