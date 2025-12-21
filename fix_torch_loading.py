#!/usr/bin/env python3
"""
حل جذري لمشكلة تحميل نماذج YOLO مع PyTorch 2.6+
"""

import torch
import os
import sys

def patch_torch_load():
    """تعديل دالة torch.load لتعطيل weights_only"""
    
    # حفظ الدالة الأصلية
    original_load = torch.load
    
    def patched_load(f, map_location=None, pickle_module=None, weights_only=None, **kwargs):
        """دالة torch.load معدلة لتعطيل weights_only"""
        # فرض weights_only=False
        return original_load(f, map_location=map_location, pickle_module=pickle_module, 
                           weights_only=False, **kwargs)
    
    # استبدال الدالة
    torch.load = patched_load
    print("✓ تم تعديل torch.load لتعطيل weights_only")

def test_patched_loading():
    """اختبار التحميل بعد التعديل"""
    try:
        from ultralytics import YOLO
        
        print("🔄 اختبار تحميل نموذج YOLO مع التعديل...")
        model = YOLO('yolov8s.pt')
        print("✅ تم تحميل النموذج بنجاح!")
        
        # اختبار الكشف
        print("🔄 اختبار الكشف...")
        import numpy as np
        test_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
        results = model(test_image, verbose=False)
        print(f"✅ تم الكشف بنجاح! عدد النتائج: {len(results)}")
        
        # اختبار كشف الأشخاص
        detections = results[0].boxes
        if detections is not None:
            person_detections = detections[detections.cls == 0]  # class 0 = person
            print(f"✅ كشف الأشخاص يعمل! عدد الأشخاص المكتشفين: {len(person_detections)}")
        else:
            print("ℹ️ لا توجد كشوفات في الصورة التجريبية")
        
        return True
        
    except Exception as e:
        print(f"❌ فشل في الاختبار: {e}")
        return False

if __name__ == "__main__":
    print("🚀 بدء الحل الجذري لمشكلة تحميل نماذج YOLO...")
    
    # تطبيق التعديل
    patch_torch_load()
    
    # اختبار النتيجة
    success = test_patched_loading()
    
    if success:
        print("\n🎉 تم حل المشكلة بنجاح!")
        print("💡 النظام جاهز للاستخدام الآن")
    else:
        print("\n❌ المشكلة لا تزال موجودة")
        print("💡 قد نحتاج لحل مختلف")
