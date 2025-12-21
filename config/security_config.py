"""
إعدادات الأمان للتطبيق
Security Configuration

يستخدم متغيرات البيئة للمفاتيح الحساسة مع توليد تلقائي إذا لم تكن موجودة.
"""
import os
import secrets
from pathlib import Path

# مسار ملف المفتاح السري (للبيئات التي لا تدعم متغيرات البيئة)
SECRET_KEY_FILE = Path(__file__).parent / ".secret_key"


def get_secret_key() -> str:
    """
    الحصول على المفتاح السري بالترتيب التالي:
    1. متغير البيئة FLASK_SECRET_KEY
    2. ملف .secret_key المحلي
    3. توليد مفتاح جديد وحفظه
    
    Returns:
        str: المفتاح السري
    """
    # أولاً: محاولة الحصول من متغير البيئة
    secret_key = os.environ.get("FLASK_SECRET_KEY")
    if secret_key:
        return secret_key
    
    # ثانياً: محاولة القراءة من ملف
    if SECRET_KEY_FILE.exists():
        try:
            secret_key = SECRET_KEY_FILE.read_text(encoding="utf-8").strip()
            if len(secret_key) >= 32:
                return secret_key
        except Exception:
            pass
    
    # ثالثاً: توليد مفتاح جديد
    secret_key = secrets.token_hex(32)
    
    # حفظ المفتاح في ملف
    try:
        SECRET_KEY_FILE.write_text(secret_key, encoding="utf-8")
        # تقييد صلاحيات الملف (Unix فقط)
        try:
            os.chmod(SECRET_KEY_FILE, 0o600)
        except (OSError, AttributeError):
            pass  # Windows لا يدعم chmod بنفس الطريقة
    except Exception:
        pass  # استخدام المفتاح حتى لو فشل الحفظ
    
    return secret_key


def get_database_url() -> str:
    """الحصول على رابط قاعدة البيانات"""
    return os.environ.get(
        "DATABASE_URL", 
        "sqlite:///attendance_db/attendance.db"
    )


def is_production() -> bool:
    """التحقق من بيئة الإنتاج"""
    return os.environ.get("FLASK_ENV", "development").lower() == "production"


def get_allowed_hosts() -> list:
    """الحصول على قائمة المضيفين المسموح بهم"""
    hosts = os.environ.get("ALLOWED_HOSTS", "127.0.0.1,localhost")
    return [h.strip() for h in hosts.split(",")]


# ثوابت الأمان
SESSION_COOKIE_SECURE = is_production()  # HTTPS only في الإنتاج
SESSION_COOKIE_HTTPONLY = True  # منع JavaScript من الوصول
SESSION_COOKIE_SAMESITE = "Lax"  # حماية من CSRF
PERMANENT_SESSION_LIFETIME = 3600  # ساعة واحدة
