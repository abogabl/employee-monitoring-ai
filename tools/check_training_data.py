"""
أداة للتحقق من بيانات التدريب قبل بدء عملية التدريب.
Pre-training data validation tool.

الاستخدام:
python tools/check_training_data.py --faces-dir employees_database/faces/
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

from tabulate import tabulate


def check_directory_structure(faces_dir: Path) -> Dict[str, List[Path]]:
    """فحص بنية المجلدات وجمع الصور."""
    employees = {}
    
    if not faces_dir.exists():
        return employees
    
    for emp_dir in sorted(faces_dir.iterdir()):
        if not emp_dir.is_dir() or emp_dir.name.startswith('.'):
            continue
        
        emp_id = emp_dir.name
        images = sorted([
            p for p in emp_dir.glob("*.*")
            if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".gif"}
        ])
        
        employees[emp_id] = images
    
    return employees


def get_employee_name(emp_dir: Path) -> str:
    """قراءة اسم الموظف."""
    name_file = emp_dir / "name.txt"
    if name_file.exists():
        try:
            return name_file.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    return emp_dir.name


def main() -> None:
    parser = argparse.ArgumentParser(description="فحص بيانات التدريب")
    parser.add_argument(
        "--faces-dir",
        default="employees_database/faces/",
        help="مجلد صور الموظفين"
    )
    parser.add_argument(
        "--min-images",
        type=int,
        default=3,
        help="الحد الأدنى الموصى به للصور"
    )
    args = parser.parse_args()
    
    faces_dir = Path(args.faces_dir)
    
    print("=" * 70)
    print(f"🔍 فحص بيانات التدريب")
    print("=" * 70)
    print(f"المجلد: {faces_dir.absolute()}")
    
    # فحص وجود المجلد
    if not faces_dir.exists():
        print(f"\n❌ خطأ: المجلد غير موجود!")
        print(f"\n💡 قم بإنشاء المجلد:")
        print(f"   mkdir -p {faces_dir}")
        print(f"\n💡 البنية المطلوبة:")
        print(f"   {faces_dir}/")
        print(f"   ├── EMP001/")
        print(f"   │   ├── name.txt      (اختياري: اسم الموظف)")
        print(f"   │   ├── photo1.jpg")
        print(f"   │   ├── photo2.jpg")
        print(f"   │   └── photo3.jpg")
        print(f"   └── EMP002/")
        print(f"       └── ...")
        return
    
    # جمع البيانات
    employees = check_directory_structure(faces_dir)
    
    if not employees:
        print(f"\n❌ لم يتم العثور على أي موظفين!")
        print(f"\n💡 تأكد من:")
        print(f"   1. وجود مجلدات فرعية باسم كل موظف (مثل: EMP001, EMP002)")
        print(f"   2. وجود صور داخل كل مجلد موظف")
        print(f"   3. امتدادات الصور صحيحة (.jpg, .jpeg, .png)")
        return
    
    # إحصائيات
    total_images = sum(len(imgs) for imgs in employees.values())
    avg_images = total_images / len(employees)
    
    print(f"\n✅ تم العثور على:")
    print(f"   - {len(employees)} موظف")
    print(f"   - {total_images} صورة إجمالاً")
    print(f"   - {avg_images:.1f} صورة في المتوسط لكل موظف")
    
    # جدول التفاصيل
    print(f"\n📊 تفاصيل الموظفين:")
    print("=" * 70)
    
    table_data = []
    warnings = []
    
    for emp_id, images in sorted(employees.items()):
        emp_dir = faces_dir / emp_id
        name = get_employee_name(emp_dir)
        num_images = len(images)
        
        # الحالة
        if num_images == 0:
            status = "❌"
            notes = "لا توجد صور!"
            warnings.append(f"{emp_id}: لا توجد صور")
        elif num_images < args.min_images:
            status = "⚠️"
            notes = f"قليل (<{args.min_images})"
            warnings.append(f"{emp_id}: فقط {num_images} صور (يُفضل {args.min_images}+)")
        elif num_images < 5:
            status = "✅"
            notes = "مقبول"
        else:
            status = "✅✅"
            notes = "ممتاز"
        
        # معلومات إضافية
        has_name_file = "✓" if (emp_dir / "name.txt").exists() else ""
        
        table_data.append([
            status,
            emp_id,
            name,
            num_images,
            has_name_file,
            notes
        ])
    
    print(tabulate(
        table_data,
        headers=["حالة", "ID", "الاسم", "عدد الصور", "ملف الاسم", "ملاحظات"],
        tablefmt="grid"
    ))
    
    # التحذيرات
    if warnings:
        print(f"\n⚠️  تحذيرات ({len(warnings)}):")
        for w in warnings:
            print(f"   - {w}")
    
    # التوصيات
    print(f"\n💡 التوصيات:")
    
    if avg_images < 3:
        print(f"   ❌ متوسط الصور منخفض جداً ({avg_images:.1f})")
        print(f"   💡 أضف المزيد من الصور لكل موظف")
        print(f"   💡 الحد الأدنى الموصى به: {args.min_images} صور")
        print(f"   💡 المثالي: 5-10 صور متنوعة")
    elif avg_images < 5:
        print(f"   ⚠️  متوسط الصور مقبول ({avg_images:.1f})")
        print(f"   💡 يمكن التحسين بإضافة المزيد من الصور")
    else:
        print(f"   ✅ متوسط الصور جيد ({avg_images:.1f})")
    
    print(f"\n📝 معايير جودة الصور:")
    print(f"   ✅ الوجه واضح وكامل")
    print(f"   ✅ إضاءة جيدة")
    print(f"   ✅ دقة عالية (640x640+ بكسل)")
    print(f"   ✅ زوايا متنوعة (أمامي، جانبي)")
    print(f"   ✅ تعبيرات مختلفة")
    
    # الخطوة التالية
    if warnings:
        print(f"\n⚠️  يُنصح بتصحيح التحذيرات قبل التدريب")
    else:
        print(f"\n✅ البيانات جاهزة للتدريب!")
    
    print(f"\n🚀 الخطوة التالية:")
    print(f"   python tools/train_faces_improved.py \\")
    print(f"       --faces-dir {faces_dir} \\")
    print(f"       --output models/face_encodings.pkl \\")
    print(f"       --threshold 0.7 \\")
    print(f"       --check-quality")


if __name__ == "__main__":
    main()
