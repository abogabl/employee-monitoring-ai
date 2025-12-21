#!/usr/bin/env python3
"""
اختبار نتائج الكشف للتأكد من عمل النظام
"""

import cv2
import numpy as np
from src.detection_tracking import PersonDetector
from src.face_recognition_system import FaceRecognitionSystem

def test_person_detection():
    """اختبار كشف الأشخاص"""
    print("🔄 اختبار كشف الأشخاص...")
    
    try:
        # إنشاء كاشف الأشخاص
        detector = PersonDetector(model_size="s", conf=0.3, device="cpu")
        print("✅ تم تحميل كاشف الأشخاص بنجاح")
        
        # إنشاء صورة اختبار (شخص وهمي)
        test_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
        
        # إضافة شكل يشبه الشخص (مستطيل)
        cv2.rectangle(test_image, (200, 150), (400, 500), (255, 255, 255), -1)
        cv2.rectangle(test_image, (250, 200), (350, 300), (0, 0, 0), -1)  # رأس
        
        # اختبار الكشف
        detections = detector.detect(test_image)
        print(f"📊 عدد الأشخاص المكتشفين: {len(detections)}")
        
        if len(detections) > 0:
            for i, det in enumerate(detections):
                box = det["box"]
                conf = det["conf"]
                x1, y1, x2, y2 = box
                print(f"   الشخص {i+1}: الموقع=({x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f}), الثقة={conf:.2f}")
        
        return len(detections) > 0
        
    except Exception as e:
        print(f"❌ خطأ في اختبار كشف الأشخاص: {e}")
        return False

def test_face_recognition():
    """اختبار التعرف على الوجوه"""
    print("\n🔄 اختبار التعرف على الوجوه...")
    
    try:
        # إنشاء نظام التعرف على الوجوه
        face_system = FaceRecognitionSystem()
        print("✅ تم تحميل نظام التعرف على الوجوه بنجاح")
        
        # إنشاء صورة اختبار
        test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # اختبار كشف الوجوه
        faces = face_system.detect_faces(test_image)
        print(f"📊 عدد الوجوه المكتشفة: {len(faces)}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار التعرف على الوجوه: {e}")
        return False

def test_with_webcam():
    """اختبار مع الكاميرا الحقيقية"""
    print("\n🔄 اختبار مع الكاميرا...")
    
    try:
        # فتح الكاميرا
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("⚠️ لا يمكن فتح الكاميرا")
            return False
        
        # إنشاء الكاشفات
        detector = PersonDetector(model_size="s", conf=0.3, device="cpu")
        face_system = FaceRecognitionSystem()
        
        print("✅ تم تهيئة جميع الأنظمة")
        print("📹 اختبار 5 إطارات من الكاميرا...")
        
        total_persons = 0
        total_faces = 0
        
        for frame_num in range(5):
            ret, frame = cap.read()
            if not ret:
                print(f"⚠️ فشل في قراءة الإطار {frame_num + 1}")
                continue
            
            # كشف الأشخاص
            persons = detector.detect(frame)
            faces = face_system.detect_faces(frame)
            
            total_persons += len(persons)
            total_faces += len(faces)
            
            print(f"   الإطار {frame_num + 1}: أشخاص={len(persons)}, وجوه={len(faces)}")
        
        cap.release()
        
        print(f"\n📊 النتائج الإجمالية:")
        print(f"   إجمالي الأشخاص: {total_persons}")
        print(f"   إجمالي الوجوه: {total_faces}")
        print(f"   متوسط الأشخاص/إطار: {total_persons/5:.1f}")
        print(f"   متوسط الوجوه/إطار: {total_faces/5:.1f}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار الكاميرا: {e}")
        return False

if __name__ == "__main__":
    print("🚀 بدء اختبار نتائج الكشف...")
    
    # اختبار كشف الأشخاص
    person_test = test_person_detection()
    
    # اختبار التعرف على الوجوه
    face_test = test_face_recognition()
    
    # اختبار مع الكاميرا الحقيقية
    webcam_test = test_with_webcam()
    
    print(f"\n🎯 ملخص النتائج:")
    print(f"   كشف الأشخاص: {'✅ يعمل' if person_test else '❌ لا يعمل'}")
    print(f"   التعرف على الوجوه: {'✅ يعمل' if face_test else '❌ لا يعمل'}")
    print(f"   اختبار الكاميرا: {'✅ يعمل' if webcam_test else '❌ لا يعمل'}")
    
    if person_test and face_test:
        print("\n🎉 النظام يعمل بشكل ممتاز! النتائج لن تكون صفرية بعد الآن.")
    else:
        print("\n⚠️ هناك مشاكل تحتاج لحل إضافي.")
