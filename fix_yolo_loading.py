#!/usr/bin/env python3
"""
إصلاح مشكلة تحميل نماذج YOLO مع PyTorch 2.6+
"""

import torch
import os

def fix_yolo_loading():
    """إصلاح مشكلة تحميل نماذج YOLO"""
    
    # الطريقة الأولى: تعطيل weights_only عالمياً
    try:
        os.environ['TORCH_WEIGHTS_ONLY'] = 'False'
        print("✓ تم تعطيل weights_only عبر متغير البيئة")
    except Exception as e:
        print(f"⚠️ فشل في تعطيل weights_only: {e}")
    
    # الطريقة الثانية: إضافة الفئات الآمنة
    try:
        if hasattr(torch.serialization, 'add_safe_globals'):
            # إضافة فئات PyTorch الأساسية
            torch_classes = [
                torch.nn.modules.container.Sequential,
                torch.nn.modules.container.ModuleList,
                torch.nn.Conv2d,
                torch.nn.BatchNorm2d,
                torch.nn.Linear,
                torch.nn.ReLU,
                torch.nn.SiLU,
                torch.nn.LeakyReLU,
                torch.nn.Upsample,
                torch.nn.MaxPool2d,
                torch.nn.ConvTranspose2d,
                torch.nn.Identity,
                torch.nn.Dropout,
            ]
            
            # إضافة فئات Ultralytics
            try:
                from ultralytics.nn.tasks import DetectionModel, SegmentationModel, ClassificationModel
                from ultralytics.nn.modules import Conv, C2f, SPPF, Bottleneck, Detect
                
                ultralytics_classes = [
                    DetectionModel,
                    SegmentationModel, 
                    ClassificationModel,
                    Conv,
                    C2f,
                    SPPF,
                    Bottleneck,
                    Detect,
                ]
                
                all_classes = torch_classes + ultralytics_classes
                torch.serialization.add_safe_globals(all_classes)
                print(f"✓ تم إضافة {len(all_classes)} فئة آمنة")
                
            except ImportError as e:
                # إضافة فئات PyTorch فقط
                torch.serialization.add_safe_globals(torch_classes)
                print(f"✓ تم إضافة {len(torch_classes)} فئة PyTorch آمنة")
                print(f"⚠️ لم يتم العثور على فئات Ultralytics: {e}")
                
    except Exception as e:
        print(f"⚠️ فشل في إضافة الفئات الآمنة: {e}")

def test_yolo_loading():
    """اختبار تحميل نماذج YOLO"""
    try:
        from ultralytics import YOLO
        
        # اختبار تحميل النموذج
        print("🔄 اختبار تحميل نموذج YOLO...")
        model = YOLO('yolov8s.pt')
        print("✅ تم تحميل النموذج بنجاح!")
        
        # اختبار الكشف
        print("🔄 اختبار الكشف...")
        import numpy as np
        test_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
        results = model(test_image, verbose=False)
        print(f"✅ تم الكشف بنجاح! عدد النتائج: {len(results)}")
        
        return True
        
    except Exception as e:
        print(f"❌ فشل في تحميل النموذج: {e}")
        return False

if __name__ == "__main__":
    print("🚀 بدء إصلاح مشكلة تحميل نماذج YOLO...")
    
    # تطبيق الإصلاحات
    fix_yolo_loading()
    
    # اختبار النتيجة
    success = test_yolo_loading()
    
    if success:
        print("\n🎉 تم إصلاح المشكلة بنجاح!")
        print("💡 يمكنك الآن استخدام النظام بشكل طبيعي")
    else:
        print("\n❌ لم يتم حل المشكلة بالكامل")
        print("💡 جرب إعادة تشغيل Python أو استخدام إصدار أقدم من PyTorch")
