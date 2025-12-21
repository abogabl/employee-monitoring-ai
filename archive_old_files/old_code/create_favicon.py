#!/usr/bin/env python3
"""
إنشاء favicon بسيط
"""
import cv2
import numpy as np

def create_favicon():
    """إنشاء favicon بسيط"""
    
    # إعدادات الأيقونة
    size = 32
    
    # إنشاء صورة زرقاء
    img = np.ones((size, size, 3), dtype=np.uint8) * 50
    img[:, :, 0] = 100  # أزرق
    
    # رسم عين (كاميرا)
    cv2.circle(img, (size//2, size//2), size//3, (255, 255, 255), 2)
    cv2.circle(img, (size//2, size//2), size//6, (255, 255, 255), -1)
    
    # حفظ كـ PNG أولاً
    cv2.imwrite("web_app/static/favicon.png", img)
    print("Created favicon.png")

if __name__ == "__main__":
    create_favicon()
