"""
سكريبت اختبار النظام المحسّن
يختبر Advanced Activity Detector و Enhanced Face Recognition
"""
import sys
import io
import cv2
import numpy as np
from pathlib import Path

# إصلاح encoding في Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# التحقق من المتطلبات
try:
    from src.advanced_activity_detector import AdvancedActivityDetector
    print("✓ Advanced Activity Detector متاح")
except Exception as e:
    print(f"⚠️ خطأ في تحميل Advanced Activity Detector: {e}")
    print("  تأكد من تثبيت mediapipe: pip install mediapipe")

try:
    from src.enhanced_face_recognition import EnhancedFaceRecognition
    print("✓ Enhanced Face Recognition متاح")
except Exception as e:
    print(f"⚠️ خطأ في تحميل Enhanced Face Recognition: {e}")
    print("  تأكد من تثبيت insightface: pip install insightface")

from ultralytics import YOLO
import time


def test_activity_detection():
    """اختبار كشف الأنشطة المحسّن"""
    print("\n" + "="*60)
    print("🎯 اختبار Advanced Activity Detector")
    print("="*60)
    
    try:
        # إنشاء detector
        detector = AdvancedActivityDetector(
            use_pose=True,
            use_optical_flow=True,
            temporal_window=30
        )
        print("✓ تم إنشاء Detector بنجاح")
        
        # إنشاء YOLO للكشف
        yolo = YOLO('yolov8n.pt')
        print("✓ تم تحميل YOLO")
        
        # فتح كاميرا أو فيديو للاختبار
        print("\n📹 جاري فتح الكاميرا...")
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("⚠️ لا يمكن فتح الكاميرا، جرب فيديو تجريبي")
            # يمكن استخدام فيديو بدلاً
            # cap = cv2.VideoCapture('test_video.mp4')
            return
        
        print("✓ تم فتح الكاميرا بنجاح")
        print("\n🔍 ابدأ الاختبار - اضغط 'q' للخروج")
        print("-" * 60)
        
        frame_count = 0
        start_time = time.time()
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            current_time = time.time() - start_time
            
            # كشف الأشخاص والأشياء
            results = yolo(frame, verbose=False)
            
            detections = []
            person_boxes = []
            
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    xyxy = box.xyxy[0].cpu().numpy()
                    
                    # حفظ الكشوفات
                    detections.append({
                        'class': cls,
                        'confidence': conf,
                        'box': xyxy.tolist()
                    })
                    
                    # حفظ boxes الأشخاص
                    if cls == 0:  # person
                        person_boxes.append(xyxy)
            
            # تحليل كل شخص
            for i, person_box in enumerate(person_boxes):
                x1, y1, x2, y2 = person_box.astype(int)
                
                # كشف النشاط
                activity, confidence, details = detector.detect_activity(
                    frame=frame,
                    person_box=(x1, y1, x2, y2),
                    track_id=i,
                    yolo_detections=detections,
                    frame_time=current_time
                )
                
                # رسم النتائج
                color = (0, 255, 0) if confidence > 0.7 else (0, 165, 255)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                
                # النص
                text = f"{activity}: {confidence:.1%}"
                cv2.putText(frame, text, (x1, y1-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                # تفاصيل إضافية
                if details['pose_detected']:
                    posture_text = f"Posture: {details['posture']}"
                    cv2.putText(frame, posture_text, (x1, y2+20),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                motion_text = f"Motion: {details['motion_level']:.2f}"
                cv2.putText(frame, motion_text, (x1, y2+40),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # FPS
            fps = frame_count / (time.time() - start_time)
            cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # عرض
            cv2.imshow('Advanced Activity Detection', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
        
        print("\n✓ اكتمل الاختبار بنجاح")
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        import traceback
        traceback.print_exc()


def test_face_recognition():
    """اختبار التعرف على الوجوه المحسّن"""
    print("\n" + "="*60)
    print("👤 اختبار Enhanced Face Recognition")
    print("="*60)
    
    try:
        # إنشاء نظام
        face_system = EnhancedFaceRecognition(
            similarity_threshold=0.45,
            quality_threshold=0.3
        )
        print("✓ تم إنشاء Face Recognition بنجاح")
        
        # إحصائيات
        stats = face_system.get_statistics()
        print(f"\n📊 الإحصائيات:")
        print(f"  - عدد الموظفين: {stats['total_employees']}")
        print(f"  - إجمالي Embeddings: {stats['total_embeddings']}")
        print(f"  - متوسط Embeddings لكل موظف: {stats['average_embeddings_per_employee']:.1f}")
        
        # اختبار على كاميرا
        print("\n📹 جاري فتح الكاميرا للاختبار...")
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("⚠️ لا يمكن فتح الكاميرا")
            return
        
        print("✓ تم فتح الكاميرا")
        print("\n🔍 ابدأ الاختبار - اضغط 'q' للخروج, 'c' لالتقاط صورة وإضافة موظف")
        print("-" * 60)
        
        capture_mode = False
        captured_images = []
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # التعرف على الوجوه
            results = face_system.recognize_multiple_faces(frame)
            
            # رسم النتائج
            for result in results:
                x1, y1, x2, y2 = result['bbox']
                emp_id = result['employee_id']
                confidence = result['confidence']
                quality = result['quality']
                
                if emp_id:
                    color = (0, 255, 0)
                    text = f"{emp_id}: {confidence:.1%}"
                else:
                    color = (0, 0, 255)
                    text = "Unknown"
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, text, (x1, y1-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                # جودة الوجه
                quality_text = f"Q: {quality:.2f}"
                cv2.putText(frame, quality_text, (x1, y2+20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # عرض
            if capture_mode:
                cv2.putText(frame, "CAPTURE MODE - Press 'c' to add", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            cv2.imshow('Enhanced Face Recognition', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('c'):
                if not capture_mode:
                    capture_mode = True
                    captured_images = []
                    print("\n📸 وضع الالتقاط مفعّل - اضغط 'c' 5 مرات لالتقاط صور")
                else:
                    captured_images.append(frame.copy())
                    print(f"  ✓ تم التقاط صورة {len(captured_images)}/5")
                    
                    if len(captured_images) >= 5:
                        emp_id = input("\nأدخل معرف الموظف: ")
                        
                        result = face_system.add_employee(
                            employee_id=emp_id,
                            images=captured_images
                        )
                        
                        if result['success']:
                            print(f"✓ {result['message']}")
                        else:
                            print(f"❌ {result['message']}")
                        
                        capture_mode = False
                        captured_images = []
        
        cap.release()
        cv2.destroyAllWindows()
        
        print("\n✓ اكتمل الاختبار بنجاح")
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        import traceback
        traceback.print_exc()


def main():
    """تشغيل جميع الاختبارات"""
    print("\n" + "="*60)
    print("🚀 اختبار النظام المحسّن")
    print("="*60)
    
    print("\nاختر الاختبار:")
    print("1. Activity Detection (كشف الأنشطة)")
    print("2. Face Recognition (التعرف على الوجوه)")
    print("3. الاثنان معاً")
    
    choice = input("\nاختيارك (1/2/3): ").strip()
    
    if choice == '1':
        test_activity_detection()
    elif choice == '2':
        test_face_recognition()
    elif choice == '3':
        test_activity_detection()
        print("\n" + "="*60)
        input("اضغط Enter للانتقال إلى اختبار التعرف على الوجوه...")
        test_face_recognition()
    else:
        print("❌ اختيار غير صحيح")


if __name__ == "__main__":
    main()
