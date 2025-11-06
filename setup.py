# سكريبت تهيئة بنية المشروع على Windows باستخدام pathlib
# يقوم بإنشاء جميع المجلدات المطلوبة ووضع ملف .gitkeep داخل كل مجلد
from pathlib import Path

# الجذر للمشروع
PROJECT_ROOT = Path(__file__).parent.resolve()

# قائمة المجلدات المطلوب إنشاؤها
DIRS = [
    PROJECT_ROOT / "src",
    PROJECT_ROOT / "employees_database" / "faces",
    PROJECT_ROOT / "models",
    PROJECT_ROOT / "reports",
    PROJECT_ROOT / "attendance_db",
    PROJECT_ROOT / "videos",
    PROJECT_ROOT / "logs",
]


def touch_gitkeep(path: Path) -> None:
    """إنشاء ملف .gitkeep داخل المجلد (إن لم يكن موجوداً)."""
    try:
        (path / ".gitkeep").touch(exist_ok=True)
    except Exception as e:
        print(f"تحذير: فشل إنشاء .gitkeep في {path}: {e}")


def main() -> None:
    # إنشاء جميع المجلدات المطلوبة
    for d in DIRS:
        d.mkdir(parents=True, exist_ok=True)
        touch_gitkeep(d)
    print("تم إنشاء بنية المجلدات بنجاح.")
    for d in DIRS:
        print(f"- {d.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
