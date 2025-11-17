# 📋 متطلبات النظام المحدث - Updated System Requirements

## 🖥️ متطلبات الأجهزة

### **الحد الأدنى:**
- **المعالج:** Intel i5 أو AMD Ryzen 5 (الجيل الرابع أو أحدث)
- **الذاكرة:** 8 GB RAM
- **التخزين:** 20 GB مساحة فارغة
- **كرت الشاشة:** مدمج (Intel HD Graphics أو أفضل)

### **الموصى به:**
- **المعالج:** Intel i7 أو AMD Ryzen 7 (الجيل السادس أو أحدث)
- **الذاكرة:** 16 GB RAM أو أكثر
- **التخزين:** 50 GB مساحة فارغة (SSD مفضل)
- **كرت الشاشة:** NVIDIA GTX 1060 أو أفضل (اختياري للسرعة)

---

## 🐍 متطلبات البرمجيات

### **Python:**
```
Python 3.8+ (الموصى به: Python 3.10)
```

### **المكتبات الأساسية:**
```bash
pip install -r requirements.txt
```

### **محتويات requirements.txt:**
```
opencv-python==4.8.1.78
ultralytics==8.0.196
torch==2.0.1
torchvision==0.15.2
numpy==1.24.3
pandas==2.0.3
scikit-learn==1.3.0
flask==2.3.3
flask-login==0.6.3
werkzeug==2.3.7
pillow==10.0.0
tqdm==4.66.1
pathlib
collections
datetime
logging
typing
argparse
```

---

## 📁 بنية المشروع المحدثة

```
employee-monitoring-ai/
├── 📁 src/
│   ├── 🔥 level2_video_processor.py    # المعالج الجديد
│   ├── 🧠 advanced_behavior_ai.py      # الذكاء الاصطناعي المتقدم
│   ├── 📊 smart_video_processor.py     # المعالج الأساسي
│   ├── 👤 face_recognition_system.py   # نظام التعرف على الوجوه
│   ├── 🎯 activity_recognition.py      # كشف الأنشطة
│   └── 🛠️ utils.py                     # أدوات مساعدة
├── 📁 web_app/
│   ├── 🌐 app.py                       # التطبيق الرئيسي
│   ├── 📁 templates/                   # قوالب HTML
│   └── 📁 static/                      # الملفات الثابتة
├── 📁 config/
│   ├── ⚙️ level2_config.json          # إعدادات المستوى الثاني
│   ├── 👤 face_recognition_config.json
│   └── 🎯 activity_config.json
├── 📁 models/                          # النماذج المدربة
├── 📁 data/                           # البيانات
└── 📋 config.json                     # الإعدادات الرئيسية
```

---

## 🔧 خطوات التثبيت

### **1. استنساخ المشروع:**
```bash
git clone [repository-url]
cd employee-monitoring-ai
```

### **2. إنشاء بيئة افتراضية:**
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

### **3. تثبيت المتطلبات:**
```bash
pip install -r requirements.txt
```

### **4. تحميل النماذج:**
```bash
# سيتم تحميلها تلقائياً عند أول تشغيل
python quick_test.py
```

### **5. تشغيل النظام:**
```bash
python run_web_app.py
```

---

## 🌐 متطلبات الشبكة

### **المنافذ المطلوبة:**
- **8080** - واجهة الويب الرئيسية
- **5000** - API (اختياري)

### **الاتصال بالإنترنت:**
- **مطلوب لأول مرة** - تحميل النماذج
- **اختياري بعد ذلك** - يعمل بدون إنترنت

---

## 📊 متطلبات الأداء

### **للفيديوهات:**
- **الدقة:** 480p إلى 4K
- **المدة:** حتى 10 دقائق (قابل للتخصيص)
- **الصيغ:** MP4, AVI, MOV, MKV
- **معدل الإطارات:** 15-60 FPS

### **للكاميرات المباشرة:**
- **USB Webcam** - مدعوم
- **IP Camera** - مدعوم (RTSP)
- **CCTV Systems** - مدعوم

---

## ⚡ تحسينات الأداء

### **للأجهزة الضعيفة:**
```json
{
  "yolo": {
    "model": "yolov8n.pt",
    "imgsz": 320,
    "confidence": 0.4
  },
  "level2_processor": {
    "frame_skip": 5,
    "max_duration": 60
  }
}
```

### **للأجهزة القوية:**
```json
{
  "yolo": {
    "model": "yolov8l.pt",
    "imgsz": 640,
    "confidence": 0.3
  },
  "level2_processor": {
    "frame_skip": 1,
    "max_duration": 600
  }
}
```

---

## 🔍 اختبار النظام

### **اختبار سريع:**
```bash
python quick_test.py
```

### **اختبار شامل:**
```bash
python test_processor.py
```

### **اختبار الواجهة:**
```
1. افتح: http://localhost:8080
2. اذهب إلى: /test-video
3. ارفع فيديو تجريبي
4. تحقق من النتائج
```

---

## ⚠️ استكشاف الأخطاء

### **مشاكل شائعة:**

#### **خطأ في تثبيت torch:**
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

#### **خطأ في OpenCV:**
```bash
pip uninstall opencv-python
pip install opencv-python-headless
```

#### **نقص في الذاكرة:**
- قلل `imgsz` في الإعدادات
- زد `frame_skip`
- قلل `max_duration`

---

## 📞 الدعم الفني

### **للمساعدة:**
1. تحقق من ملف `logs/app.log`
2. راجع `TEAM_UPDATE_GUIDE.md`
3. تواصل مع الفريق التقني

### **معلومات النظام:**
- **الإصدار:** Level 2 Advanced AI
- **تاريخ التحديث:** نوفمبر 2025
- **الحالة:** مستقر وجاهز للإنتاج

---

## 🎯 الخلاصة

النظام جاهز للعمل مع:
- ✅ جميع المتطلبات محددة بوضوح
- ✅ خطوات التثبيت مفصلة
- ✅ إعدادات محسنة للأداء
- ✅ دليل استكشاف الأخطاء

**جاهز للتوزيع على الفريق! 🚀**
