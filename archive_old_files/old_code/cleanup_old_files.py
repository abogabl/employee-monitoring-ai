#!/usr/bin/env python3
"""
سكريبت تنظيف الملفات القديمة غير المستخدمة
يحتفظ فقط بالملفات المحسنة والضرورية
"""

import os
import shutil
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("cleanup")

def cleanup_old_files():
    """تنظيف الملفات القديمة"""
    project_root = Path(__file__).resolve().parent
    
    # الملفات القديمة التي يمكن حذفها
    old_processors = [
        "src/simple_video_processor.py",  # استبدل بـ smart_video_processor
        "src/enhanced_video_processor.py",  # استبدل بـ smart_video_processor  
        "src/fast_video_processor.py",  # استبدل بـ smart_video_processor
    ]
    
    # ملفات الاختبار القديمة
    old_test_files = [
        "test_level1_improvements.py",
        "test_enhanced_system.py",
        "quick_test.py",
    ]
    
    # مجلدات قديمة
    old_dirs = [
        "archive_old_files",  # مجلد الأرشيف القديم
    ]
    
    logger.info("🧹 بدء تنظيف الملفات القديمة...")
    
    # حذف المعالجات القديمة
    logger.info("📁 حذف المعالجات القديمة...")
    for file_path in old_processors:
        full_path = project_root / file_path
        if full_path.exists():
            try:
                full_path.unlink()
                logger.info(f"✓ تم حذف: {file_path}")
            except Exception as e:
                logger.error(f"❌ فشل حذف {file_path}: {e}")
    
    # حذف ملفات الاختبار القديمة
    logger.info("🧪 حذف ملفات الاختبار القديمة...")
    for file_path in old_test_files:
        full_path = project_root / file_path
        if full_path.exists():
            try:
                full_path.unlink()
                logger.info(f"✓ تم حذف: {file_path}")
            except Exception as e:
                logger.error(f"❌ فشل حذف {file_path}: {e}")
    
    # حذف المجلدات القديمة
    logger.info("📂 حذف المجلدات القديمة...")
    for dir_path in old_dirs:
        full_path = project_root / dir_path
        if full_path.exists():
            try:
                shutil.rmtree(full_path)
                logger.info(f"✓ تم حذف المجلد: {dir_path}")
            except Exception as e:
                logger.error(f"❌ فشل حذف المجلد {dir_path}: {e}")
    
    # تنظيف ملفات __pycache__
    logger.info("🗂️ تنظيف ملفات التخزين المؤقت...")
    pycache_dirs = list(project_root.rglob("__pycache__"))
    for pycache_dir in pycache_dirs:
        try:
            shutil.rmtree(pycache_dir)
            logger.info(f"✓ تم حذف: {pycache_dir.relative_to(project_root)}")
        except Exception as e:
            logger.error(f"❌ فشل حذف {pycache_dir}: {e}")
    
    # تنظيف ملفات .pyc
    logger.info("🐍 تنظيف ملفات .pyc...")
    pyc_files = list(project_root.rglob("*.pyc"))
    for pyc_file in pyc_files:
        try:
            pyc_file.unlink()
            logger.info(f"✓ تم حذف: {pyc_file.relative_to(project_root)}")
        except Exception as e:
            logger.error(f"❌ فشل حذف {pyc_file}: {e}")
    
    logger.info("✨ تم الانتهاء من التنظيف!")

def show_current_structure():
    """عرض البنية الحالية للمشروع"""
    project_root = Path(__file__).resolve().parent
    
    logger.info("📋 البنية الحالية للمشروع:")
    
    # الملفات الرئيسية
    main_files = [
        "run_smart_camera.py",
        "run_web_app.py", 
        "train_faces.py",
        "generate_report.py",
    ]
    
    logger.info("🎯 الملفات الرئيسية:")
    for file_name in main_files:
        file_path = project_root / file_name
        status = "✓" if file_path.exists() else "❌"
        logger.info(f"  {status} {file_name}")
    
    # المعالجات المحسنة
    processors = [
        "src/smart_video_processor.py",
        "src/smart_camera_processor.py",
        "src/main_production_smart.py",
    ]
    
    logger.info("🧠 المعالجات المحسنة:")
    for file_name in processors:
        file_path = project_root / file_name
        status = "✓" if file_path.exists() else "❌"
        logger.info(f"  {status} {file_name}")
    
    # المجلدات المهمة
    important_dirs = [
        "src",
        "web_app", 
        "config",
        "docs",
        "tests",
    ]
    
    logger.info("📁 المجلدات المهمة:")
    for dir_name in important_dirs:
        dir_path = project_root / dir_name
        status = "✓" if dir_path.exists() else "❌"
        logger.info(f"  {status} {dir_name}/")

def main():
    """الدالة الرئيسية"""
    import argparse
    
    parser = argparse.ArgumentParser(description="تنظيف الملفات القديمة")
    parser.add_argument("--dry-run", action="store_true", help="عرض ما سيتم حذفه فقط")
    parser.add_argument("--show-structure", action="store_true", help="عرض بنية المشروع")
    
    args = parser.parse_args()
    
    if args.show_structure:
        show_current_structure()
        return
    
    if args.dry_run:
        logger.info("🔍 وضع المعاينة - لن يتم حذف أي ملفات")
        # يمكن إضافة منطق المعاينة هنا
        return
    
    # تأكيد من المستخدم
    response = input("⚠️  هل أنت متأكد من حذف الملفات القديمة؟ (y/N): ")
    if response.lower() != 'y':
        logger.info("تم الإلغاء")
        return
    
    cleanup_old_files()
    show_current_structure()

if __name__ == "__main__":
    main()
