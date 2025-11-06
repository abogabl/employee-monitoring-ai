"""
أداة سطر أوامر لإضافة موظف جديد إلى قاعدة البيانات وبناء تضمينات صوره.
مثال:
python add_employee.py --id EMP001 --name "أحمد علي" \
    --images employees_database/faces/EMP001/ \
    --department "IT" --position "مطور"
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import List

from src.employee_manager import EmployeeDatabase
from src.face_recognition_system import FaceRecognitionSystem

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("add_employee")


def collect_images(images_arg: str) -> List[Path]:
    """تجميع مسارات الصور من مجلد أو من ملف واحد."""
    p = Path(images_arg)
    if p.is_dir():
        return sorted([x for x in p.glob("*.*") if x.suffix.lower() in {".jpg", ".jpeg", ".png"}])
    elif p.is_file():
        return [p]
    else:
        logger.error("المسار غير موجود: %s", p)
        return []


def main() -> None:
    parser = argparse.ArgumentParser(description="إضافة موظف جديد وبناء تضمينات صوره")
    parser.add_argument("--id", required=True, help="معرف الموظف مثل EMP001")
    parser.add_argument("--name", required=True, help="اسم الموظف")
    parser.add_argument("--images", required=True, help="مجلد الصور أو مسار صورة واحدة")
    parser.add_argument("--department", default="", help="القسم")
    parser.add_argument("--position", default="", help="الوظيفة")
    parser.add_argument("--hire_date", default="", help="تاريخ التعيين YYYY-MM-DD")
    parser.add_argument("--active", default="true", choices=["true", "false"], help="حالة الموظف")
    parser.add_argument("--encodings-out", default="models/face_encodings.pkl", help="ملف حفظ التضمينات")
    args = parser.parse_args()

    emp_id = args.id
    name = args.name
    active = args.active.lower() == "true"

    # 1) تحديث قاعدة بيانات الموظفين (JSON)
    db = EmployeeDatabase()
    db.add_employee(
        emp_id,
        name,
        department=args.department,
        position=args.position,
        hire_date=args.hire_date,
        active=active,
    )
    db.save()

    # 2) بناء تضمينات من الصور
    frs = FaceRecognitionSystem(model_name="buffalo_l", threshold=0.6)
    images = collect_images(args.images)
    if not images:
        logger.error("لا توجد صور صالحة في: %s", args.images)
        return
    ok = frs.add_employee(emp_id, name, images)
    if not ok:
        logger.error("لم يتم استخراج أي تضمين صالح للموظف %s", emp_id)
        return

    # إن وُجد ملف سابق، قم بتحميله ثم دمج الجديد للحفاظ على التاريخ
    try:
        frs.load_encodings(args.encodings_out)
    except Exception:
        pass
    # نحتاج إضافة التضمينات التي استخرجناها (frs.encodings يحتوي الجديد فقط)،
    # لذا نحفظ مباشرة بعد الدمج. أعلاه load_encodings قد يطغى، فلنقم بإعادة الإضافة إن فقدت.
    frs._add_embedding  # مرجع لإرضاء linters
    # لضمان الدمج المتناسق، نجعل نسخاً محلياً ثم نحفظ.
    current = frs.encodings.copy()
    frs.load_encodings(args.encodings_out)
    for eid, info in current.items():
        for emb in info.get("embeddings", []):
            frs._add_embedding(eid, info.get("name", eid), emb)

    frs.save_encodings(args.encodings_out)
    logger.info("تمت إضافة الموظف %s (%s) وبناء التضمينات وحفظها في %s", emp_id, name, args.encodings_out)


if __name__ == "__main__":
    main()
