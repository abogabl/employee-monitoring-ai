#!/usr/bin/env python3
"""
اختبار مع صورة حقيقية من الإنترنت
"""

import cv2
import numpy as np
import requests
from io import BytesIO
from PIL import Image

# تطبيق الإصلاح أولاً
import torch
import os

# تعطيل weights_only عالمياً
os.environ['TORCH_WEIGHTS_ONLY'] = 'False'

# تعديل دالة torch.load
if hasattr(torch, 'load'):
    original_load = torch.load
    
    def patched_load(f, map_location=None, pickle_module=None, weights_only=None, **kwargs):
        return original_load(f, map_location=map_location, pickle_module=pickle_module, 
                           weights_only=False, **kwargs)
    
    torch.load = patched_load
    print("✓ تم تطبيق إصلاح torch.load")

from src.detection_tracking import PersonDetector

def download_test_image():
    """تحميل صورة اختبار تحتوي على أشخاص"""
    try:
        # صورة اختبار من Ultralytics
        url = "https://ultralytics.com/images/bus.jpg"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            # تحويل إلى صورة OpenCV
            image = Image.open(BytesIO(response.content))
            image = image.convert('RGB')
            opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            print(f"✅ تم تحميل صورة اختبار بحجم: {opencv_image.shape}")
            return opencv_image
        else:
            print(f"❌ فشل تحميل الصورة: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ خطأ في تحميل الصورة: {e}")
        return None

def create_simple_person():
    """إنشاء صورة بسيطة تحتوي على شكل شخص واضح"""
    # صورة بخلفية بيضاء
    img = np.ones((640, 640, 3), dtype=np.uint8) * 255
    
    # رسم شخص بسيط وواضح
    # الجسم (مستطيل كبير)
    cv2.rectangle(img, (200, 200), (440, 600), (50, 50, 50), -1)
    
    # الرأس (دائرة)
    cv2.circle(img, (320, 120), 80, (100, 100, 100), -1)
    
    # الذراعين
    cv2.rectangle(img, (120, 250), (200, 450), (70, 70, 70), -1)
    cv2.rectangle(img, (440, 250), (520, 450), (70, 70, 70), -1)
    
    # الساقين
    cv2.rectangle(img, (230, 600), (290, 630), (30, 30, 30), -1)
    cv2.rectangle(img, (350, 600), (410, 630), (30, 30, 30), -1)
    
    # إضافة بعض التفاصيل
    cv2.circle(img, (290, 100), 10, (0, 0, 0), -1)  # عين
    cv2.circle(img, (350, 100), 10, (0, 0, 0), -1)  # عين
    
    return img

def test_detection_with_images():
    """اختبار الكشف مع صور مختلفة"""
    print("🚀 اختبار كشف الأشخاص مع صور حقيقية...")
    
    try:
        # إنشاء الكاشف
        detector = PersonDetector(model_size="s", conf=0.25, device="cpu")
        print("✅ تم تحميل PersonDetector")
        
        # اختبار 1: صورة من الإنترنت
        print("\n🔄 اختبار 1: صورة من الإنترنت...")
        web_image = download_test_image()
        if web_image is not None:
            detections = detector.detect(web_image)
            print(f"📊 عدد الكشوفات في صورة الإنترنت: {len(detections)}")
            
            for i, det in enumerate(detections):
                if det["class"] == 0:  # شخص
                    conf = det["conf"]
                    print(f"   ✅ شخص {i+1}: ثقة={conf:.2f}")
        
        # اختبار 2: صورة مرسومة
        print("\n🔄 اختبار 2: صورة مرسومة...")
        drawn_image = create_simple_person()
        detections = detector.detect(drawn_image)
        print(f"📊 عدد الكشوفات في الصورة المرسومة: {len(detections)}")
        
        for i, det in enumerate(detections):
            conf = det["conf"]
            cls = det["class"]
            print(f"   الكشف {i+1}: فئة={cls}, ثقة={conf:.2f}")
            if cls == 0:
                print(f"   ✅ تم كشف شخص!")
        
        # حفظ الصورة المرسومة للفحص
        cv2.imwrite("test_person_image.jpg", drawn_image)
        print("💾 تم حفظ الصورة المرسومة كـ test_person_image.jpg")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في الاختبار: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_detection_with_images()
    
    if success:
        print("\n🎉 الاختبار اكتمل!")
        print("💡 إذا لم يتم كشف أشخاص، فالمشكلة في عتبة الثقة أو جودة الصورة")
    else:
        print("\n❌ فشل الاختبار")
        print("💡 تحقق من الأخطاء أعلاه")
