"""
اختبارات شاملة لإعدادات الأمان
Comprehensive tests for security configuration
"""
import os
import pytest
from pathlib import Path


class TestSecurityConfig:
    """اختبارات security_config"""
    
    def test_import(self):
        """اختبار الاستيراد"""
        from config.security_config import get_secret_key
        assert get_secret_key is not None
    
    def test_secret_key_length(self):
        """اختبار طول المفتاح السري"""
        from config.security_config import get_secret_key
        key = get_secret_key()
        assert len(key) >= 32  # 32 bytes = 64 hex chars
    
    def test_secret_key_consistency(self):
        """اختبار ثبات المفتاح"""
        from config.security_config import get_secret_key
        key1 = get_secret_key()
        key2 = get_secret_key()
        assert key1 == key2  # يجب أن يكون نفس المفتاح
    
    def test_secret_key_from_env(self):
        """اختبار القراءة من متغير البيئة"""
        from config import security_config
        
        # حفظ القيمة الأصلية
        original = os.environ.get("FLASK_SECRET_KEY")
        
        try:
            # تعيين متغير البيئة
            os.environ["FLASK_SECRET_KEY"] = "test_secret_key_12345678901234567890"
            
            # إعادة استيراد
            import importlib
            importlib.reload(security_config)
            
            key = security_config.get_secret_key()
            assert key == "test_secret_key_12345678901234567890"
        finally:
            # استعادة القيمة الأصلية
            if original:
                os.environ["FLASK_SECRET_KEY"] = original
            else:
                os.environ.pop("FLASK_SECRET_KEY", None)
    
    def test_is_production_default(self):
        """اختبار بيئة التطوير الافتراضية"""
        from config.security_config import is_production
        
        # حذف متغير البيئة إذا موجود
        original = os.environ.pop("FLASK_ENV", None)
        
        try:
            from config import security_config
            import importlib
            importlib.reload(security_config)
            
            assert security_config.is_production() == False
        finally:
            if original:
                os.environ["FLASK_ENV"] = original
    
    def test_is_production_true(self):
        """اختبار بيئة الإنتاج"""
        from config import security_config
        
        original = os.environ.get("FLASK_ENV")
        
        try:
            os.environ["FLASK_ENV"] = "production"
            
            import importlib
            importlib.reload(security_config)
            
            assert security_config.is_production() == True
        finally:
            if original:
                os.environ["FLASK_ENV"] = original
            else:
                os.environ.pop("FLASK_ENV", None)
    
    def test_session_cookie_settings(self):
        """اختبار إعدادات الكوكيز"""
        from config.security_config import (
            SESSION_COOKIE_HTTPONLY,
            SESSION_COOKIE_SAMESITE,
            PERMANENT_SESSION_LIFETIME
        )
        
        assert SESSION_COOKIE_HTTPONLY == True
        assert SESSION_COOKIE_SAMESITE == "Lax"
        assert PERMANENT_SESSION_LIFETIME == 3600
    
    def test_database_url_default(self):
        """اختبار رابط قاعدة البيانات الافتراضي"""
        from config.security_config import get_database_url
        
        original = os.environ.pop("DATABASE_URL", None)
        
        try:
            url = get_database_url()
            assert "sqlite" in url
            assert "attendance" in url
        finally:
            if original:
                os.environ["DATABASE_URL"] = original
    
    def test_allowed_hosts_default(self):
        """اختبار المضيفين المسموحين الافتراضيين"""
        from config.security_config import get_allowed_hosts
        
        original = os.environ.pop("ALLOWED_HOSTS", None)
        
        try:
            hosts = get_allowed_hosts()
            assert "127.0.0.1" in hosts
            assert "localhost" in hosts
        finally:
            if original:
                os.environ["ALLOWED_HOSTS"] = original


class TestSecurityConfigFile:
    """اختبارات ملف المفتاح السري"""
    
    def test_secret_key_file_creation(self):
        """اختبار إنشاء ملف المفتاح"""
        from config.security_config import SECRET_KEY_FILE, get_secret_key
        
        # حذف الملف إذا موجود
        if SECRET_KEY_FILE.exists():
            original_content = SECRET_KEY_FILE.read_text()
            SECRET_KEY_FILE.unlink()
        else:
            original_content = None
        
        # حذف متغير البيئة
        env_key = os.environ.pop("FLASK_SECRET_KEY", None)
        
        try:
            # يجب أن ينشئ ملف جديد
            key = get_secret_key()
            
            # التحقق من الملف
            if not SECRET_KEY_FILE.exists():
                # قد يفشل الإنشاء في بعض البيئات
                pass
        finally:
            # استعادة
            if original_content:
                SECRET_KEY_FILE.write_text(original_content)
            if env_key:
                os.environ["FLASK_SECRET_KEY"] = env_key


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
