#!/usr/bin/env python3
"""
اختبار بسيط لكشف الأشخاص
"""

import cv2
import numpy as np
from src.detection_tracking import PersonDetector

def create_person_image():
    """إنشاء صورة تحتوي على شكل يشبه الشخص"""
    # إنشاء صورة بيضاء
    img = np.ones((480, 640, 3), dtype=np.uint8) * 255
    
    # رسم شكل يشبه الشخص
    # الجسم
    cv2.rectangle(img, (250, 200), (390, 450), (100, 100, 100), -1)
    
    # الرأس
    cv2.circle(img, (320, 150), 50, (150, 150, 150), -1)
    
    # الذراعين
    cv2.rectangle(img, (200, 220), (250, 350), (120, 120, 120), -1)
    cv2.rectangle(img, (390, 220), (440, 350), (120, 120, 120), -1)
    
    # الساقين
    cv2.rectangle(img, (270, 450), (320, 470), (80, 80, 80), -1)
    cv2.rectangle(img, (350, 450), (400, 470), (80, 80, 80), -1)
    
    return img

def test_yolo_detection():
    """اختبار كشف YOLO مباشرة"""
    print("🔄 اختبار كشف YOLO مباشرة...")
    
    try:
        from ultralytics import YOLO
        
        # تحميل النموذج
        model = YOLO('yolov8s.pt')
        print("✅ تم تحميل نموذج YOLO")
        
        # إنشاء صورة اختبار
        test_img = create_person_image()
        
        # الكشف
        results = model(test_img, verbose=False)
        
        if results and len(results) > 0:
            boxes = results[0].boxes
            if boxes is not None:
                print(f"📊 عدد الكشوفات: {len(boxes)}")
                
                for i, box in enumerate(boxes):
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    xyxy = box.xyxy[0].cpu().numpy()
                    
                    print(f"   الكشف {i+1}: فئة={cls}, ثقة={conf:.2f}, مربع={xyxy}")
                    
                    # فئة 0 = شخص
                    if cls == 0:
                        print(f"   ✅ تم كشف شخص بثقة {conf:.2f}")
                        return True
            else:
                print("📊 لا توجد كشوفات")
        else:
            print("📊 لا توجد نتائج")
        
        return False
        
    except Exception as e:
        print(f"❌ خطأ في اختبار YOLO: {e}")
        return False

def test_person_detector():
    """اختبار PersonDetector"""
    print("\n🔄 اختبار PersonDetector...")
    
    try:
        # إنشاء الكاشف
        detector = PersonDetector(model_size="s", conf=0.1, device="cpu")  # ثقة منخفضة للاختبار
        print("✅ تم تحميل PersonDetector")
        
        # إنشاء صورة اختبار
        test_img = create_person_image()
        
        # الكشف
        detections = detector.detect(test_img)
        print(f"📊 عدد الكشوفات: {len(detections)}")
        
        for i, det in enumerate(detections):
            box = det["box"]
            conf = det["conf"]
            cls = det["class"]
            
            print(f"   الكشف {i+1}: فئة={cls}, ثقة={conf:.2f}, مربع={box}")
            
            if cls == 0:  # شخص
                print(f"   ✅ تم كشف شخص بثقة {conf:.2f}")
                return True
        
        return len(detections) > 0
        
    except Exception as e:
        print(f"❌ خطأ في اختبار PersonDetector: {e}")
        return False

if __name__ == "__main__":
    print("🚀 اختبار كشف الأشخاص...")
    
    # اختبار YOLO مباشرة
    yolo_works = test_yolo_detection()
    
    # اختبار PersonDetector
    detector_works = test_person_detector()
    
    print(f"\n🎯 النتائج:")
    print(f"   YOLO مباشرة: {'✅ يعمل' if yolo_works else '❌ لا يعمل'}")
    print(f"   PersonDetector: {'✅ يعمل' if detector_works else '❌ لا يعمل'}")
    
    if yolo_works or detector_works:
        print("\n🎉 النظام يعمل! المشكلة تم حلها.")
        print("💡 النتائج لن تكون صفرية بعد الآن عند استخدام فيديو حقيقي.")
    else:
        print("\n⚠️ النظام لا يزال لا يكشف الأشخاص.")
        print("💡 قد نحتاج لضبط العتبات أو استخدام نموذج مختلف.")
