"""
بناء قاعدة تضمينات وجوه الموظفين باستخدام InsightFace.
يقرأ جميع مجلدات الموظفين داخل employees_database/faces/ ويحفظ ملف التضمينات.
مثال:
python train_faces.py --faces-dir employees_database/faces/ --output models/face_encodings.pkl
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.face_recognition_system import FaceRecognitionSystem

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("train_faces")


def main() -> None:
    parser = argparse.ArgumentParser(description="بناء تضمينات وجوه الموظفين")
    parser.add_argument("--faces-dir", default="employees_database/faces/", help="مجلد صور الموظفين")
    parser.add_argument("--output", default="models/face_encodings.pkl", help="مسار حفظ ملف التضمينات")
    parser.add_argument("--model", default="buffalo_l", help="اسم نموذج InsightFace")
    parser.add_argument("--threshold", type=float, default=0.6, help="حد التشابه لاستخدامه لاحقاً")
    args = parser.parse_args()

    faces_dir = Path(args.faces_dir)
    if not faces_dir.exists():
        logger.error("مجلد الوجوه غير موجود: %s", faces_dir)
        return

    frs = FaceRecognitionSystem(model_name=args.model, threshold=args.threshold)
    frs.load_employees_database(faces_dir)

    # إحصائيات
    num_employees = len(frs.encodings)
    logger.info("عدد الموظفين الذين بُنيت لهم تضمينات: %d", num_employees)
    for emp_id, info in sorted(frs.encodings.items()):
        name = info.get("name", emp_id)
        num_imgs = len(info.get("embeddings", []))
        logger.info("- %s (%s): %d صورة", emp_id, name, num_imgs)

    out_path = Path(args.output)
    frs.save_encodings(out_path)


if __name__ == "__main__":
    main()
