#!/usr/bin/env python3
"""
إنشاء فيديو تجريبي للاختبار
"""
import cv2
import numpy as np
import os

def create_test_video(output_path="test_video.mp4", duration=5, fps=30):
    """إنشاء فيديو تجريبي بسيط"""
    
    # إعدادات الفيديو
    width, height = 640, 480
    total_frames = duration * fps
    
    # إنشاء كاتب الفيديو
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    print(f"Creating test video: {output_path}")
    print(f"Duration: {duration}s, FPS: {fps}, Frames: {total_frames}")
    
    for frame_num in range(total_frames):
        # إنشاء إطار أزرق
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:, :] = (100, 50, 0)  # لون أزرق داكن
        
        # رسم مستطيل متحرك (يمثل شخص)
        x = int(50 + (frame_num / total_frames) * (width - 150))
        y = int(height // 2 - 50)
        
        # رسم "شخص" بسيط
        cv2.rectangle(frame, (x, y), (x + 100, y + 100), (0, 255, 0), -1)  # جسم أخضر
        cv2.circle(frame, (x + 50, y - 20), 20, (255, 255, 255), -1)  # رأس أبيض
        
        # إضافة نص
        cv2.putText(frame, f"Frame {frame_num + 1}/{total_frames}", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        cv2.putText(frame, f"Test Person Moving", 
                   (10, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        out.write(frame)
        
        if frame_num % 30 == 0:
            print(f"Progress: {(frame_num / total_frames) * 100:.1f}%")
    
    out.release()
    
    # التحقق من الملف
    if os.path.exists(output_path):
        file_size = os.path.getsize(output_path) / 1024  # KB
        print(f"Video created successfully!")
        print(f"Path: {output_path}")
        print(f"Size: {file_size:.1f} KB")
        
        # اختبار قراءة الفيديو
        cap = cv2.VideoCapture(output_path)
        if cap.isOpened():
            fps_check = cap.get(cv2.CAP_PROP_FPS)
            frames_check = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            print(f"Video readable: {frames_check} frames, {fps_check} FPS")
            cap.release()
        else:
            print("Failed to read created video")
    else:
        print("Failed to create video")

if __name__ == "__main__":
    # إنشاء فيديو تجريبي في مجلد الرفع
    upload_dir = "web_app/static/uploads/test_videos"
    os.makedirs(upload_dir, exist_ok=True)
    
    output_path = os.path.join(upload_dir, "test_sample.mp4")
    create_test_video(output_path, duration=3, fps=30)
