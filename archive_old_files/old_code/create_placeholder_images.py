#!/usr/bin/env python3
"""
إنشاء صور placeholder للاختبار
"""
import cv2
import numpy as np
import os

def create_placeholder_image(output_path, person_id=1):
    """إنشاء صورة placeholder لشخص"""
    
    # إعدادات الصورة
    width, height = 150, 200
    
    # إنشاء صورة رمادية
    img = np.ones((height, width, 3), dtype=np.uint8) * 128
    
    # رسم "شخص" بسيط
    # الرأس
    cv2.circle(img, (width//2, 50), 25, (200, 200, 200), -1)
    
    # الجسم
    cv2.rectangle(img, (width//2-20, 75), (width//2+20, 150), (180, 180, 180), -1)
    
    # الذراعين
    cv2.rectangle(img, (width//2-40, 85), (width//2-20, 120), (160, 160, 160), -1)
    cv2.rectangle(img, (width//2+20, 85), (width//2+40, 120), (160, 160, 160), -1)
    
    # الساقين
    cv2.rectangle(img, (width//2-15, 150), (width//2-5, 190), (160, 160, 160), -1)
    cv2.rectangle(img, (width//2+5, 150), (width//2+15, 190), (160, 160, 160), -1)
    
    # إضافة نص
    cv2.putText(img, f"Person {person_id}", (10, height-10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # حفظ الصورة
    cv2.imwrite(output_path, img)
    print(f"Created placeholder: {output_path}")

if __name__ == "__main__":
    # إنشاء مجلد الصور
    snapshots_dir = "web_app/static/uploads/test_videos/snapshots"
    os.makedirs(snapshots_dir, exist_ok=True)
    
    # إنشاء صور placeholder
    for i in range(1, 5):
        output_path = os.path.join(snapshots_dir, f"person_{i}_placeholder.jpg")
        create_placeholder_image(output_path, i)
