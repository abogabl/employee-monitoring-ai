"""
أداة للتحقق من جودة صور الوجوه قبل التدريب.
Face image quality validation tool.

الاستخدام:
python tools/validate_face_images.py --faces-dir employees_database/faces/
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

import cv2
import numpy as np
from tabulate import tabulate


class FaceImageValidator:
    """مُحقق جودة صور الوجوه."""
    
    def __init__(
        self,
        min_size: int = 200,
        min_brightness: int = 40,
        max_brightness: int = 220,
        min_sharpness: float = 100.0
    ):
        self.min_size = min_size
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.min_sharpness = min_sharpness
        
        # كاشف الوجوه
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
    
    def validate_image(self, img_path: Path) -> Dict[str, Any]:
        """
        التحقق من صورة واحدة.
        
        Returns:
            dict مع معلومات التحقق والجودة
        """
        result = {
            'path': str(img_path),
            'valid': True,
            'errors': [],
            'warnings': [],
            'quality_score': 100.0,
            'details': {}
        }
        
        # قراءة الصورة
        img = cv2.imread(str(img_path))
        if img is None:
            result['valid'] = False
            result['errors'].append("فشل قراءة الصورة")
            result['quality_score'] = 0.0
            return result
        
        h, w = img.shape[:2]
        result['details']['dimensions'] = f"{w}x{h}"
        
        # 1. فحص الحجم
        if min(h, w) < self.min_size:
            result['warnings'].append(
                f"حجم صغير: {w}x{h} (يُفضل >{self.min_size}x{self.min_size})"
            )
            result['quality_score'] -= 15
        
        # 2. فحص الإضاءة
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        brightness = float(np.mean(gray))
        result['details']['brightness'] = f"{brightness:.1f}"
        
        if brightness < self.min_brightness:
            result['warnings'].append(
                f"إضاءة منخفضة: {brightness:.1f} (يُفضل >{self.min_brightness})"
            )
            result['quality_score'] -= 25
        elif brightness > self.max_brightness:
            result['warnings'].append(
                f"إضاءة عالية: {brightness:.1f} (يُفضل <{self.max_brightness})"
            )
            result['quality_score'] -= 15
        
        # 3. فحص الوضوح
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness = float(laplacian.var())
        result['details']['sharpness'] = f"{sharpness:.1f}"
        
        if sharpness < self.min_sharpness:
            result['warnings'].append(
                f"صورة مشوشة: {sharpness:.1f} (يُفضل >{self.min_sharpness})"
            )
            result['quality_score'] -= 30
        
        # 4. كشف الوجوه
        faces = self.face_cascade.detectMultiScale(
            gray, 1.1, 4, minSize=(50, 50)
        )
        
        num_faces = len(faces)
        result['details']['faces_detected'] = num_faces
        
        if num_faces == 0:
            result['errors'].append("لم يتم اكتشاف وجه")
            result['quality_score'] -= 50
            result['valid'] = False
        elif num_faces > 1:
            result['warnings'].append(
                f"عدة وجوه ({num_faces}) - يُفضل وجه واحد فقط"
            )
            result['quality_score'] -= 20
        else:
            # فحص حجم الوجه
            x, y, w_f, h_f = faces[0]
            face_area = w_f * h_f
            img_area = w * h
            face_ratio = (face_area / img_area) * 100
            result['details']['face_ratio'] = f"{face_ratio:.1f}%"
            
            if face_ratio < 10:
                result['warnings'].append(
                    f"وجه صغير: {face_ratio:.1f}% من الصورة (يُفضل >15%)"
                )
                result['quality_score'] -= 20
            elif face_ratio > 80:
                result['warnings'].append(
                    f"وجه كبير جداً: {face_ratio:.1f}% (قد يكون قص زائد)"
                )
                result['quality_score'] -= 10
        
        # 5. فحص التشبع
        if len(img.shape) == 3:
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            saturation = float(np.mean(hsv[:, :, 1]))
            result['details']['saturation'] = f"{saturation:.1f}"
            
            if saturation < 20:
                result['warnings'].append("ألوان باهتة")
                result['quality_score'] -= 5
        
        # تحديد الصحة النهائية
        result['quality_score'] = max(0.0, result['quality_score'])
        if result['quality_score'] < 50:
            result['valid'] = False
            result['errors'].append("جودة منخفضة جداً")
        
        return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="التحقق من جودة صور الوجوه"
    )
    parser.add_argument(
        "--faces-dir",
        default="employees_database/faces/",
        help="مجلد صور الموظفين"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="عرض تفاصيل كل صورة"
    )
    parser.add_argument(
        "--output",
        help="حفظ التقرير في ملف"
    )
    args = parser.parse_args()
    
    faces_dir = Path(args.faces_dir)
    
    print("=" * 70)
    print("🔍 التحقق من جودة صور الوجوه")
    print("=" * 70)
    print(f"المجلد: {faces_dir.absolute()}\n")
    
    if not faces_dir.exists():
        print(f"❌ المجلد غير موجود: {faces_dir}")
        return
    
    # جمع الصور
    all_results: Dict[str, List[Dict[str, Any]]] = {}
    validator = FaceImageValidator()
    
    for emp_dir in sorted(faces_dir.iterdir()):
        if not emp_dir.is_dir() or emp_dir.name.startswith('.'):
            continue
        
        emp_id = emp_dir.name
        images = sorted([
            p for p in emp_dir.glob("*.*")
            if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}
        ])
        
        if not images:
            continue
        
        print(f"📂 {emp_id} ({len(images)} صور)...")
        
        emp_results = []
        for img_path in images:
            result = validator.validate_image(img_path)
            emp_results.append(result)
            
            if args.verbose:
                status = "✅" if result['valid'] else "❌"
                score = result['quality_score']
                print(f"  {status} {img_path.name}: {score:.0f}%")
                if result['errors']:
                    for err in result['errors']:
                        print(f"      ❌ {err}")
                if result['warnings']:
                    for warn in result['warnings'][:2]:
                        print(f"      ⚠️  {warn}")
        
        all_results[emp_id] = emp_results
    
    # إحصائيات إجمالية
    print("\n" + "=" * 70)
    print("📊 ملخص النتائج")
    print("=" * 70)
    
    table_data = []
    total_images = 0
    total_valid = 0
    total_invalid = 0
    
    for emp_id, results in sorted(all_results.items()):
        num_images = len(results)
        num_valid = sum(1 for r in results if r['valid'])
        num_invalid = num_images - num_valid
        avg_quality = np.mean([r['quality_score'] for r in results])
        
        total_images += num_images
        total_valid += num_valid
        total_invalid += num_invalid
        
        status = "✅" if num_invalid == 0 else "⚠️" if num_valid >= 3 else "❌"
        
        table_data.append([
            status,
            emp_id,
            num_images,
            num_valid,
            num_invalid,
            f"{avg_quality:.0f}%"
        ])
    
    print("\n" + tabulate(
        table_data,
        headers=["حالة", "ID", "إجمالي", "صالحة", "غير صالحة", "متوسط الجودة"],
        tablefmt="grid"
    ))
    
    print(f"\n📈 الإجمالي:")
    print(f"   - مجموع الصور: {total_images}")
    print(f"   - صور صالحة: {total_valid} ({total_valid/total_images*100:.1f}%)")
    print(f"   - صور غير صالحة: {total_invalid} ({total_invalid/total_images*100:.1f}%)")
    
    # المشاكل الشائعة
    all_warnings = {}
    all_errors = {}
    
    for emp_id, results in all_results.items():
        for result in results:
            for err in result['errors']:
                all_errors[err] = all_errors.get(err, 0) + 1
            for warn in result['warnings']:
                # استخلاص نوع التحذير فقط
                warn_type = warn.split(':')[0].strip()
                all_warnings[warn_type] = all_warnings.get(warn_type, 0) + 1
    
    if all_errors:
        print(f"\n❌ أخطاء شائعة:")
        for err, count in sorted(all_errors.items(), key=lambda x: -x[1])[:5]:
            print(f"   - {err}: {count} صورة")
    
    if all_warnings:
        print(f"\n⚠️  تحذيرات شائعة:")
        for warn, count in sorted(all_warnings.items(), key=lambda x: -x[1])[:5]:
            print(f"   - {warn}: {count} صورة")
    
    # التوصيات
    print(f"\n💡 التوصيات:")
    
    if total_invalid > total_valid * 0.3:
        print("   ❌ أكثر من 30% من الصور غير صالحة")
        print("   💡 يُنصح بتحسين جودة الصور قبل التدريب")
    elif total_invalid > 0:
        print(f"   ⚠️  {total_invalid} صور غير صالحة")
        print("   💡 يمكن التدريب، لكن يُفضل تحسين الصور غير الصالحة")
    else:
        print("   ✅ جميع الصور صالحة!")
    
    if 'لم يتم اكتشاف وجه' in all_errors:
        print("\n   💡 بعض الصور لا تحتوي على وجوه واضحة:")
        print("      - تأكد من وضوح الوجه في الصورة")
        print("      - تجنب الزوايا الشديدة")
        print("      - تحسين الإضاءة")
    
    if 'صورة مشوشة' in all_warnings or any('مشوش' in w for w in all_warnings):
        print("\n   💡 بعض الصور مشوشة:")
        print("      - استخدم كاميرا أفضل أو حسّن التركيز")
        print("      - تجنب الحركة أثناء التقاط الصورة")
    
    # حفظ التقرير
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # تكوين تقرير نصي
        report_lines = [
            "=" * 70,
            "تقرير التحقق من جودة صور الوجوه",
            "=" * 70,
            f"\nالمجلد: {faces_dir.absolute()}",
            f"\nإحصائيات:",
            f"  - مجموع الصور: {total_images}",
            f"  - صور صالحة: {total_valid} ({total_valid/total_images*100:.1f}%)",
            f"  - صور غير صالحة: {total_invalid} ({total_invalid/total_images*100:.1f}%)",
            "\nتفاصيل الموظفين:"
        ]
        
        for emp_id, results in sorted(all_results.items()):
            report_lines.append(f"\n{emp_id}:")
            for result in results:
                status = "✅" if result['valid'] else "❌"
                img_name = Path(result['path']).name
                score = result['quality_score']
                report_lines.append(f"  {status} {img_name}: {score:.0f}%")
                if result['errors']:
                    for err in result['errors']:
                        report_lines.append(f"      ❌ {err}")
                if result['warnings']:
                    for warn in result['warnings']:
                        report_lines.append(f"      ⚠️  {warn}")
        
        output_path.write_text('\n'.join(report_lines), encoding='utf-8')
        print(f"\n💾 تم حفظ التقرير: {output_path}")
    
    print(f"\n{'='*70}")
    print("✅ اكتمل التحقق!")
    print("=" * 70)
    
    if total_valid >= total_images * 0.7:
        print("\n🚀 الخطوة التالية:")
        print("   python tools/train_faces_improved.py --check-quality")
    else:
        print("\n⚠️  يُنصح بتحسين جودة الصور أولاً")


if __name__ == "__main__":
    main()
