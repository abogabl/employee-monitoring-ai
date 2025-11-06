# 🚀 دليل البدء السريع - 30 دقيقة

## الخطوة 1: التثبيت (10 دقائق)

### 1.1 تحميل المشروع
```bash
git clone https://github.com/yourrepo/employee-monitoring.git
cd employee-monitoring
```

### 1.2 إنشاء البيئة الافتراضية
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

### 1.3 تثبيت المتطلبات
```bash
pip install -r requirements.txt
```

### 1.4 إعداد الهيكل
```bash
python setup.py
```

✅ Checkpoint: يجب أن ترى "تم إنشاء بنية المجلدات بنجاح."

---

## الخطوة 2: إضافة موظف تجريبي (5 دقائق)

### 2.1 تحضير صور الموظف
ضع 5-10 صور للموظف في:
```
employees_database/faces/EMP001/
```

### 2.2 إضافة الموظف
```bash
python add_employee.py \
    --id EMP001 \
    --name "أحمد علي" \
    --images employees_database/faces/EMP001/
```

### 2.3 بناء Face Encodings
```bash
python train_faces.py
```

✅ Checkpoint: يجب أن ترى "تم بناء التضمينات" وظهور ملف models/face_encodings.pkl

---

## الخطوة 3: اختبار على فيديو (10 دقائق)

### 3.1 تحميل فيديو تجريبي
ضع فيديو تجريبي في:
```
videos/test.mp4
```

### 3.2 تشغيل النظام
```bash
python src/main_production.py \
    --source videos/test.mp4 \
    --camera-id test_cam \
    --device cpu \
    --enable-face-recognition \
    --enable-activity-recognition \
    --display
```

### 3.3 مشاهدة النتائج
- ستظهر نافذة مع الفيديو المُعالَج
- انتظر حتى ينتهي الفيديو
- ستجد التقارير في: `reports/`

✅ Checkpoint: يجب أن ترى ملفات CSV في مجلد reports

---

## الخطوة 4: عرض التقارير (5 دقائق)

### 4.1 عرض التقرير التفصيلي
```bash
python show_final_report.py
```

### 4.2 تصدير لـ Excel
```bash
python export_attendance.py \
    --start 2024-01-01 --end 2024-01-31 \
    --format excel \
    --output my_first_report.xlsx
```

✅ Checkpoint: يجب أن تجد ملف Excel مع البيانات

---

## 🎉 تهانينا!
لقد نجحت في تشغيل النظام!

### الخطوات التالية:

1. **إضافة المزيد من الموظفين**
```bash
python add_employee.py --id EMP002 --name "سارة محمد" --images employees_database/faces/EMP002/
```

2. **ربط كاميرا حقيقية**
عدّل `config/cameras_config.json`

3. **تشغيل Dashboard**
```bash
python run_web_app.py
```
افتح: http://localhost:5000

4. **تشغيل Multi-Camera**
```bash
python run_multi_camera.py
```

---

## ❓ مشاكل شائعة

### "ModuleNotFoundError"
```bash
pip install -r requirements.txt --upgrade
```

### "CUDA not available"
استخدم `--device cpu` بدلاً من `cuda`

### "Face not recognized"
- تأكد من وضوح الصور
- أضف المزيد من الصور
- اخفض threshold في الإعدادات
- أعد تدريب التضمينات

### "FPS very low"
- قلّل imgsz: `--imgsz 416`
- زد detection_interval
- استخدم GPU

---

## 📚 قراءة إضافية
- docs/user_guide.md
- docs/api_reference.md
- docs/troubleshooting.md
- docs/faq.md
