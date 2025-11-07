"""
أداة مُحسَّنة لتدريب نظام التعرف على الوجوه مع فحص جودة الصور.
Improved face training tool with quality validation and detailed statistics.

مميزات:
- فحص جودة الصور تلقائياً
- إحصائيات مفصلة لكل موظف
- تحذيرات للصور ذات الجودة المنخفضة
- تقرير شامل بعد التدريب
- دعم threshold ديناميكي

الاستخدام:
python tools/train_faces_improved.py \
    --faces-dir employees_database/faces/ \
    --output models/face_encodings.pkl \
    --threshold 0.7 \
    --min-images 3 \
    --check-quality
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np
from tabulate import tabulate

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.face_recognition_system import FaceRecognitionSystem

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("train_faces_improved")


class ImageQualityChecker:
    """فاحص جودة الصور للتعرف على الوجوه."""
    
    def __init__(self, min_size: int = 200, min_brightness: int = 40, max_brightness: int = 220):
        self.min_size = min_size
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
    
    def check_image(self, img_path: Path, img: np.ndarray) -> Dict[str, Any]:
        """
        فحص جودة صورة واحدة.
        
        Returns:
            dict: {
                'valid': bool,
                'warnings': List[str],
                'quality_score': float (0-100),
                'face_detected': bool,
                'face_size': int,
                'brightness': float,
                'sharpness': float
            }
        """
        result = {
            'valid': True,
            'warnings': [],
            'quality_score': 100.0,
            'face_detected': False,
            'face_size': 0,
            'brightness': 0.0,
            'sharpness': 0.0
        }
        
        if img is None or img.size == 0:
            result['valid'] = False
            result['warnings'].append("فشل قراءة الصورة")
            result['quality_score'] = 0.0
            return result
        
        # 1. حجم الصورة
        h, w = img.shape[:2]
        if min(h, w) < self.min_size:
            result['warnings'].append(f"حجم صغير: {w}x{h} (يُفضل > {self.min_size})")
            result['quality_score'] -= 20
        
        # 2. الإضاءة
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        brightness = float(np.mean(gray))
        result['brightness'] = brightness
        
        if brightness < self.min_brightness:
            result['warnings'].append(f"إضاءة منخفضة: {brightness:.1f} (يُفضل > {self.min_brightness})")
            result['quality_score'] -= 25
        elif brightness > self.max_brightness:
            result['warnings'].append(f"إضاءة عالية جداً: {brightness:.1f} (يُفضل < {self.max_brightness})")
            result['quality_score'] -= 15
        
        # 3. الوضوح (Sharpness) - استخدام تباين Laplacian
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness = float(laplacian.var())
        result['sharpness'] = sharpness
        
        if sharpness < 100:
            result['warnings'].append(f"صورة مشوشة: sharpness={sharpness:.1f} (يُفضل > 100)")
            result['quality_score'] -= 30
        
        # 4. كشف الوجه
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(50, 50))
        
        if len(faces) == 0:
            result['warnings'].append("لم يتم اكتشاف وجه واضح")
            result['quality_score'] -= 40
        elif len(faces) > 1:
            result['warnings'].append(f"عدة وجوه في الصورة ({len(faces)})")
            result['quality_score'] -= 20
        else:
            result['face_detected'] = True
            x, y, w_f, h_f = faces[0]
            face_area = w_f * h_f
            img_area = w * h
            face_ratio = (face_area / img_area) * 100
            result['face_size'] = int(face_ratio)
            
            if face_ratio < 10:
                result['warnings'].append(f"الوجه صغير جداً: {face_ratio:.1f}% (يُفضل > 15%)")
                result['quality_score'] -= 25
        
        # تحديد صحة الصورة
        if result['quality_score'] < 40:
            result['valid'] = False
        
        result['quality_score'] = max(0.0, result['quality_score'])
        
        return result


def collect_employee_images(faces_dir: Path) -> Dict[str, List[Path]]:
    """جمع صور كل موظف من المجلدات."""
    employees = {}
    
    if not faces_dir.exists():
        logger.error(f"مجلد الوجوه غير موجود: {faces_dir}")
        return employees
    
    for emp_dir in sorted(faces_dir.iterdir()):
        if not emp_dir.is_dir() or emp_dir.name.startswith('.'):
            continue
        
        emp_id = emp_dir.name
        images = sorted([
            p for p in emp_dir.glob("*.*")
            if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}
        ])
        
        if images:
            employees[emp_id] = images
    
    return employees


def get_employee_name(emp_dir: Path) -> str:
    """قراءة اسم الموظف من ملف name.txt أو استخدام emp_id."""
    name_file = emp_dir / "name.txt"
    if name_file.exists():
        try:
            return name_file.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    return emp_dir.name


def main() -> None:
    parser = argparse.ArgumentParser(
        description="أداة مُحسَّنة لتدريب نظام التعرف على الوجوه"
    )
    parser.add_argument(
        "--faces-dir",
        default="employees_database/faces/",
        help="مجلد صور الموظفين"
    )
    parser.add_argument(
        "--output",
        default="models/face_encodings.pkl",
        help="مسار حفظ ملف التضمينات"
    )
    parser.add_argument(
        "--model",
        default="buffalo_l",
        help="اسم نموذج InsightFace"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.7,
        help="حد التشابه (موصى به: 0.6-0.7)"
    )
    parser.add_argument(
        "--min-images",
        type=int,
        default=3,
        help="الحد الأدنى لعدد الصور لكل موظف"
    )
    parser.add_argument(
        "--check-quality",
        action="store_true",
        help="تفعيل فحص جودة الصور"
    )
    parser.add_argument(
        "--report",
        default="reports/training_report.json",
        help="مسار حفظ تقرير التدريب"
    )
    args = parser.parse_args()
    
    faces_dir = Path(args.faces_dir)
    output_path = Path(args.output)
    report_path = Path(args.report)
    
    # التحقق من وجود المجلد
    if not faces_dir.exists():
        logger.error(f"❌ مجلد الوجوه غير موجود: {faces_dir}")
        logger.info("💡 قم بإنشاء المجلد وأضف صور الموظفين:")
        logger.info(f"   mkdir -p {faces_dir}/EMP001")
        logger.info(f"   # ثم ضع صور الموظف في: {faces_dir}/EMP001/")
        return
    
    # جمع الصور
    logger.info("=" * 70)
    logger.info("🚀 بدء عملية التدريب المُحسَّنة")
    logger.info("=" * 70)
    
    employees_images = collect_employee_images(faces_dir)
    
    if not employees_images:
        logger.error("❌ لم يتم العثور على أي موظفين!")
        logger.info("💡 تأكد من البنية الصحيحة:")
        logger.info(f"   {faces_dir}/")
        logger.info(f"   ├── EMP001/")
        logger.info(f"   │   ├── name.txt")
        logger.info(f"   │   ├── photo1.jpg")
        logger.info(f"   │   └── photo2.jpg")
        logger.info(f"   └── EMP002/")
        logger.info(f"       └── ...")
        return
    
    logger.info(f"✅ تم العثور على {len(employees_images)} موظف")
    
    # فحص جودة الصور
    quality_checker = ImageQualityChecker() if args.check_quality else None
    quality_stats: Dict[str, Any] = {}
    
    if args.check_quality:
        logger.info("\n" + "=" * 70)
        logger.info("🔍 فحص جودة الصور...")
        logger.info("=" * 70)
        
        for emp_id, images in employees_images.items():
            emp_stats = {
                'total_images': len(images),
                'valid_images': 0,
                'invalid_images': 0,
                'warnings': []
            }
            
            for img_path in images:
                img = cv2.imread(str(img_path))
                check_result = quality_checker.check_image(img_path, img)
                
                if check_result['valid']:
                    emp_stats['valid_images'] += 1
                else:
                    emp_stats['invalid_images'] += 1
                
                if check_result['warnings']:
                    emp_stats['warnings'].append({
                        'image': img_path.name,
                        'warnings': check_result['warnings'],
                        'quality_score': check_result['quality_score']
                    })
            
            quality_stats[emp_id] = emp_stats
            
            # عرض التحذيرات
            if emp_stats['invalid_images'] > 0 or emp_stats['warnings']:
                logger.warning(f"\n⚠️  {emp_id}: {emp_stats['invalid_images']} صور ذات جودة منخفضة")
                for w in emp_stats['warnings'][:3]:  # أول 3 تحذيرات
                    logger.warning(f"   - {w['image']}: {', '.join(w['warnings'][:2])}")
    
    # فحص الحد الأدنى للصور
    logger.info("\n" + "=" * 70)
    logger.info("📊 إحصائيات الصور:")
    logger.info("=" * 70)
    
    table_data = []
    warnings_list = []
    
    for emp_id, images in sorted(employees_images.items()):
        emp_dir = faces_dir / emp_id
        name = get_employee_name(emp_dir)
        num_images = len(images)
        
        status = "✅"
        notes = ""
        
        if num_images < args.min_images:
            status = "⚠️"
            notes = f"قليل (<{args.min_images})"
            warnings_list.append(f"{emp_id}: فقط {num_images} صور (يُفضل {args.min_images}+)")
        
        if args.check_quality and emp_id in quality_stats:
            valid = quality_stats[emp_id]['valid_images']
            if valid < args.min_images:
                status = "⚠️"
                notes += f" | {valid} صور صالحة فقط"
        
        table_data.append([status, emp_id, name, num_images, notes])
    
    print("\n" + tabulate(
        table_data,
        headers=["حالة", "ID", "الاسم", "عدد الصور", "ملاحظات"],
        tablefmt="grid"
    ))
    
    if warnings_list:
        logger.warning("\n⚠️  تحذيرات:")
        for w in warnings_list:
            logger.warning(f"   - {w}")
    
    # بدء التدريب
    logger.info("\n" + "=" * 70)
    logger.info("🎓 بدء التدريب على النموذج...")
    logger.info("=" * 70)
    logger.info(f"النموذج: {args.model}")
    logger.info(f"Threshold: {args.threshold}")
    
    try:
        frs = FaceRecognitionSystem(
            model_name=args.model,
            threshold=args.threshold
        )
        
        # تحميل وبناء التضمينات
        frs.load_employees_database(faces_dir)
        
        # إحصائيات التدريب
        logger.info("\n" + "=" * 70)
        logger.info("✅ نتائج التدريب:")
        logger.info("=" * 70)
        
        if not frs.encodings:
            logger.error("❌ فشل التدريب: لم يتم بناء أي تضمينات!")
            logger.error("💡 تحقق من:")
            logger.error("   1. جودة الصور")
            logger.error("   2. وجود وجوه واضحة في الصور")
            logger.error("   3. تثبيت مكتبة insightface بشكل صحيح")
            return
        
        training_results = []
        total_embeddings = 0
        
        for emp_id, info in sorted(frs.encodings.items()):
            name = info.get("name", emp_id)
            num_embeddings = len(info.get("embeddings", []))
            total_embeddings += num_embeddings
            
            status = "✅" if num_embeddings >= args.min_images else "⚠️"
            training_results.append([status, emp_id, name, num_embeddings])
            
            logger.info(f"  {status} {emp_id} ({name}): {num_embeddings} تضمينات")
        
        logger.info(f"\n📈 الإجمالي:")
        logger.info(f"   - موظفون مُدرَّبون: {len(frs.encodings)}")
        logger.info(f"   - مجموع التضمينات: {total_embeddings}")
        logger.info(f"   - متوسط التضمينات لكل موظف: {total_embeddings / len(frs.encodings):.1f}")
        
        # حفظ التضمينات
        output_path.parent.mkdir(parents=True, exist_ok=True)
        frs.save_encodings(output_path)
        logger.info(f"\n💾 تم حفظ التضمينات: {output_path}")
        
        # حفظ التقرير
        report = {
            'timestamp': datetime.now().isoformat(),
            'config': {
                'model': args.model,
                'threshold': args.threshold,
                'min_images': args.min_images,
                'quality_check_enabled': args.check_quality
            },
            'statistics': {
                'total_employees': len(frs.encodings),
                'total_embeddings': total_embeddings,
                'avg_embeddings_per_employee': total_embeddings / len(frs.encodings) if frs.encodings else 0
            },
            'employees': {}
        }
        
        for emp_id, info in frs.encodings.items():
            report['employees'][emp_id] = {
                'name': info.get("name", emp_id),
                'num_embeddings': len(info.get("embeddings", [])),
                'images_found': len(employees_images.get(emp_id, [])),
                'quality_stats': quality_stats.get(emp_id, {}) if args.check_quality else None
            }
        
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        logger.info(f"📄 تم حفظ التقرير: {report_path}")
        
        # توصيات
        logger.info("\n" + "=" * 70)
        logger.info("💡 التوصيات:")
        logger.info("=" * 70)
        
        if total_embeddings / len(frs.encodings) < args.min_images:
            logger.warning("⚠️  متوسط الصور أقل من المطلوب، يُنصح بإضافة المزيد")
        
        if args.threshold > 0.75:
            logger.warning("⚠️  Threshold مرتفع (>0.75)، قد يفشل في التعرف على بعض الحالات")
            logger.info("💡  جرّب threshold=0.7 إذا واجهت مشاكل في التعرف")
        elif args.threshold < 0.6:
            logger.warning("⚠️  Threshold منخفض (<0.6)، قد يعطي تطابقات خاطئة")
            logger.info("💡  جرّب threshold=0.65 لتوازن أفضل")
        else:
            logger.info("✅ Threshold مناسب (0.6-0.75)")
        
        logger.info("\n" + "=" * 70)
        logger.info("🎉 اكتمل التدريب بنجاح!")
        logger.info("=" * 70)
        logger.info("\n🚀 الخطوات التالية:")
        logger.info("   1. اختبر النظام:")
        logger.info("      python src/main_production.py --source videos/test.mp4 --enable-face-recognition --display")
        logger.info("   2. راجع التقرير:")
        logger.info(f"      {report_path}")
        logger.info("   3. في حالة وجود مشاكل، راجع الدليل:")
        logger.info("      docs/FACE_RECOGNITION_TRAINING_GUIDE.md")
        
    except Exception as e:
        logger.exception(f"❌ حدث خطأ أثناء التدريب: {e}")
        logger.error("\n💡 حلول محتملة:")
        logger.error("   1. تأكد من تثبيت جميع المكتبات: pip install -r requirements.txt")
        logger.error("   2. تحقق من صلاحيات الملفات")
        logger.error("   3. راجع الدليل: docs/FACE_RECOGNITION_TRAINING_GUIDE.md")
        return


if __name__ == "__main__":
    main()
