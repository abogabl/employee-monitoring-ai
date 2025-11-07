"""
أداة لفحص وعرض محتويات ملف التضمينات (encodings).
Inspection tool for face encodings file - shows statistics and details.

الاستخدام:
python tools/inspect_encodings.py --input models/face_encodings.pkl
"""
from __future__ import annotations

import argparse
import pickle
from pathlib import Path
from typing import Any, Dict

import numpy as np
from tabulate import tabulate


def load_encodings(path: Path) -> Dict[str, Any]:
    """تحميل ملف التضمينات."""
    if not path.exists():
        raise FileNotFoundError(f"ملف التضمينات غير موجود: {path}")
    
    with path.open("rb") as f:
        return pickle.load(f)


def analyze_encodings(encodings: Dict[str, Any]) -> Dict[str, Any]:
    """تحليل التضمينات وإرجاع إحصائيات."""
    stats = {
        'total_employees': len(encodings),
        'total_embeddings': 0,
        'embedding_dimensions': None,
        'employees_details': []
    }
    
    for emp_id, info in encodings.items():
        name = info.get('name', emp_id)
        embs = info.get('embeddings', [])
        num_embs = len(embs)
        stats['total_embeddings'] += num_embs
        
        # حجم التضمين
        if embs and stats['embedding_dimensions'] is None:
            stats['embedding_dimensions'] = embs[0].shape[0] if hasattr(embs[0], 'shape') else len(embs[0])
        
        # حساب متوسط النورم
        norms = [np.linalg.norm(np.array(e)) for e in embs]
        avg_norm = np.mean(norms) if norms else 0.0
        std_norm = np.std(norms) if norms else 0.0
        
        stats['employees_details'].append({
            'emp_id': emp_id,
            'name': name,
            'num_embeddings': num_embs,
            'avg_norm': avg_norm,
            'std_norm': std_norm
        })
    
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="فحص ملف التضمينات")
    parser.add_argument(
        "--input",
        default="models/face_encodings.pkl",
        help="مسار ملف التضمينات"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="عرض تفاصيل إضافية"
    )
    args = parser.parse_args()
    
    enc_path = Path(args.input)
    
    print("=" * 70)
    print(f"🔍 فحص ملف التضمينات: {enc_path}")
    print("=" * 70)
    
    try:
        encodings = load_encodings(enc_path)
        stats = analyze_encodings(encodings)
        
        print(f"\n📊 إحصائيات عامة:")
        print(f"   ✅ عدد الموظفين: {stats['total_employees']}")
        print(f"   ✅ مجموع التضمينات: {stats['total_embeddings']}")
        print(f"   ✅ متوسط التضمينات/موظف: {stats['total_embeddings'] / stats['total_employees']:.1f}")
        print(f"   ✅ أبعاد التضمين: {stats['embedding_dimensions']}")
        
        # جدول الموظفين
        print(f"\n👥 تفاصيل الموظفين:")
        print("=" * 70)
        
        table_data = []
        for detail in sorted(stats['employees_details'], key=lambda x: x['emp_id']):
            status = "✅" if detail['num_embeddings'] >= 3 else "⚠️"
            
            row = [
                status,
                detail['emp_id'],
                detail['name'],
                detail['num_embeddings']
            ]
            
            if args.verbose:
                row.extend([
                    f"{detail['avg_norm']:.2f}",
                    f"{detail['std_norm']:.2f}"
                ])
            
            table_data.append(row)
        
        headers = ["حالة", "ID", "الاسم", "عدد التضمينات"]
        if args.verbose:
            headers.extend(["متوسط النورم", "انحراف النورم"])
        
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        
        # تحذيرات
        warnings = []
        for detail in stats['employees_details']:
            if detail['num_embeddings'] < 3:
                warnings.append(f"{detail['emp_id']}: فقط {detail['num_embeddings']} تضمينات (يُفضل 3+)")
        
        if warnings:
            print(f"\n⚠️  تحذيرات:")
            for w in warnings:
                print(f"   - {w}")
        
        # توصيات
        avg_embeddings = stats['total_embeddings'] / stats['total_employees']
        print(f"\n💡 التوصيات:")
        
        if avg_embeddings < 3:
            print("   ⚠️  متوسط التضمينات منخفض جداً (<3)")
            print("   💡 أضف المزيد من الصور لكل موظف (5-10 صور موصى بها)")
        elif avg_embeddings < 5:
            print("   ⚠️  متوسط التضمينات مقبول (3-5)")
            print("   💡 يمكن تحسينه بإضافة المزيد من الصور")
        else:
            print("   ✅ متوسط التضمينات جيد (5+)")
        
        print(f"\n✅ اكتمل الفحص بنجاح!")
        
    except FileNotFoundError as e:
        print(f"\n❌ خطأ: {e}")
        print("\n💡 تأكد من:")
        print("   1. تشغيل أداة التدريب أولاً:")
        print("      python train_faces.py")
        print("   2. المسار الصحيح للملف")
    except Exception as e:
        print(f"\n❌ حدث خطأ: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
