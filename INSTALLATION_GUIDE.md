# 🛠️ دليل التثبيت والتشغيل - Installation & Setup Guide

## 🚀 البدء السريع - Quick Start

### **للفريق الجديد:**
```bash
# 1. استنساخ المشروع
git clone [repository-url]
cd employee-monitoring-ai

# 2. تثبيت المتطلبات
pip install -r requirements.txt

# 3. تشغيل النظام
python run_web_app.py

# 4. فتح المتصفح
# اذهب إلى: http://localhost:8080
```

---

## 📋 خطوات التثبيت التفصيلية

### **الخطوة 1: تحضير البيئة**

#### **تثبيت Python:**
```bash
# تأكد من وجود Python 3.8+
python --version

# إذا لم يكن مثبتاً، حمل من:
# https://www.python.org/downloads/
```

#### **إنشاء بيئة افتراضية:**
```bash
# إنشاء البيئة
python -m venv employee_monitoring_env

# تفعيل البيئة
# Windows:
employee_monitoring_env\Scripts\activate
# Linux/Mac:
source employee_monitoring_env/bin/activate
```

### **الخطوة 2: تحميل المشروع**

```bash
# استنساخ المشروع
git clone [repository-url]
cd employee-monitoring-ai

# أو تحميل ZIP وفك الضغط
```

### **الخطوة 3: تثبيت المكتبات**

```bash
# تحديث pip
python -m pip install --upgrade pip

# تثبيت المتطلبات
pip install -r requirements.txt

# في حالة مشاكل torch:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### **الخطوة 4: إعداد المجلدات**

```bash
# إنشاء المجلدات المطلوبة (تلقائياً)
python -c "
from pathlib import Path
Path('models').mkdir(exist_ok=True)
Path('data/employees').mkdir(parents=True, exist_ok=True)
Path('logs').mkdir(exist_ok=True)
Path('web_app/static/uploads').mkdir(parents=True, exist_ok=True)
print('✅ تم إنشاء المجلدات')
"
```

---

## ⚙️ الإعداد والتخصيص

### **1. إعدادات النظام الأساسية:**

#### **تحرير config.json:**
```json
{
  "yolo": {
    "model": "yolov8s.pt",
    "imgsz": 416,
    "confidence": 0.35,
    "device": "cpu"
  },
  "level2_processor": {
    "enable_advanced_ai": true,
    "enable_face_recognition": true,
    "enable_activity_recognition": true,
    "frame_skip": 3,
    "max_duration": 300
  }
}
```

### **2. إعدادات الأداء:**

#### **للأجهزة الضعيفة:**
```json
{
  "yolo": {
    "model": "yolov8n.pt",
    "imgsz": 320,
    "confidence": 0.4
  },
  "level2_processor": {
    "frame_skip": 5,
    "max_duration": 60,
    "enable_advanced_ai": false
  }
}
```

#### **للأجهزة القوية:**
```json
{
  "yolo": {
    "model": "yolov8l.pt",
    "imgsz": 640,
    "confidence": 0.3
  },
  "level2_processor": {
    "frame_skip": 1,
    "max_duration": 600,
    "enable_advanced_ai": true
  }
}
```

---

## 🎯 اختبار التثبيت

### **1. اختبار سريع:**
```bash
python quick_test.py
```

**النتيجة المتوقعة:**
```
[1] Testing Enhanced Person Detection...
    [OK] Enhanced Person Detection working!
    - Model: YOLOv8s
    - Accuracy: 95%+

[2] Testing Enhanced Face Recognition...
    [OK] Enhanced Face Recognition working!
    - Employees: X
    - Embeddings: Y

[3] Testing Integration...
    [OK] Integration successful!
    - System will use enhanced detectors automatically
```

### **2. اختبار المعالج:**
```bash
python test_processor.py
```

### **3. اختبار الواجهة:**
```bash
python run_web_app.py
```

ثم اذهب إلى: `http://localhost:8080`

---

## 🌐 تشغيل النظام

### **1. التشغيل العادي:**
```bash
python run_web_app.py
```

### **2. التشغيل مع خيارات:**
```bash
# تشغيل على منفذ مختلف
python run_web_app.py --port 9090

# تشغيل في وضع التطوير
python run_web_app.py --debug

# تشغيل مع host مختلف
python run_web_app.py --host 0.0.0.0
```

### **3. التشغيل في الخلفية:**
```bash
# Windows:
start /b python run_web_app.py

# Linux:
nohup python run_web_app.py &
```

---

## 👥 إضافة الموظفين

### **1. إضافة صور الموظفين:**
```bash
# إنشاء مجلد للموظف
mkdir "data/employees/احمد_محمد"

# إضافة صور (5-10 صور مختلفة)
# ضع الصور في: data/employees/احمد_محمد/
```

### **2. تدريب النظام:**
```bash
python train_faces.py
```

### **3. اختبار التعرف:**
- ارفع فيديو يحتوي على الموظف
- تحقق من ظهور اسمه في النتائج

---

## 📊 مراقبة الأداء

### **1. مراجعة السجلات:**
```bash
# عرض آخر السجلات
tail -f logs/app.log

# البحث في السجلات
grep "ERROR" logs/app.log
```

### **2. مراقبة الموارد:**
```bash
# استخدام الذاكرة
python -c "
import psutil
print(f'RAM: {psutil.virtual_memory().percent}%')
print(f'CPU: {psutil.cpu_percent()}%')
"
```

---

## 🔧 استكشاف الأخطاء الشائعة

### **خطأ: "ModuleNotFoundError"**
```bash
# تأكد من تفعيل البيئة الافتراضية
pip install -r requirements.txt
```

### **خطأ: "CUDA not available"**
```bash
# عادي - النظام يعمل على CPU
# لا حاجة لإصلاح
```

### **خطأ: "Port already in use"**
```bash
# استخدم منفذ مختلف
python run_web_app.py --port 8081
```

### **خطأ: "Out of memory"**
```bash
# قلل حجم الصورة في config.json
"imgsz": 320
"frame_skip": 5
```

---

## 🔄 التحديثات

### **تحديث النظام:**
```bash
# سحب آخر التحديثات
git pull origin main

# تحديث المكتبات
pip install -r requirements.txt --upgrade

# إعادة تشغيل النظام
python run_web_app.py
```

### **نسخ احتياطي:**
```bash
# نسخ الإعدادات
cp config.json config_backup.json

# نسخ بيانات الموظفين
cp -r data/employees data/employees_backup
```

---

## 📞 الدعم والمساعدة

### **للمشاكل التقنية:**
1. تحقق من `logs/app.log`
2. راجع هذا الدليل
3. تواصل مع الفريق التقني

### **للاستفسارات:**
- **الواجهة:** مشاكل في التصفح
- **الأداء:** بطء في المعالجة
- **النتائج:** دقة التعرف

---

## ✅ قائمة التحقق النهائية

### **قبل التسليم للفريق:**
- [ ] Python 3.8+ مثبت
- [ ] جميع المكتبات مثبتة
- [ ] النظام يعمل بدون أخطاء
- [ ] واجهة الويب تفتح بنجاح
- [ ] اختبار رفع فيديو يعمل
- [ ] النتائج تظهر بشكل صحيح

### **للاستخدام اليومي:**
- [ ] إضافة صور الموظفين
- [ ] تدريب نظام التعرف
- [ ] اختبار جميع الميزات
- [ ] مراجعة الإعدادات
- [ ] إعداد النسخ الاحتياطي

---

## 🎉 مبروك!

**النظام جاهز للعمل! 🚀**

الآن يمكن للفريق:
- ✅ تثبيت النظام بسهولة
- ✅ تشغيله بدون مشاكل
- ✅ استخدام جميع الميزات المتقدمة
- ✅ الحصول على نتائج دقيقة

**وقت البدء: 15-30 دقيقة فقط!**
