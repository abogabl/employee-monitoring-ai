# 🎯 ملخص استراتيجية التعرف على الأنشطة
## Activity Recognition - Quick Summary

---

## 📌 الفكرة الأساسية

النظام يكتشف **5 أنشطة** للموظفين:
1. 💼 **Working** - العمل
2. 😴 **Sleeping** - النوم
3. 📱 **On Phone** - استخدام الهاتف
4. ⏸️ **Idle** - خامل
5. ❓ **Unknown** - غير معروف

---

## 🔧 المكونات الرئيسية

```
SimpleVideoProcessor
├── PersonDetector (YOLO) → كشف الأشخاص
├── PersonTracker (Centroid) → تتبع الأشخاص
└── SimpleActivityDetector (Rules) → كشف الأنشطة
```

---

## 🎬 خطوات المعالجة

```
1. قراءة الفيديو (25 fps)
2. معالجة كل إطار ثاني (frame_skip=2)
3. كشف الأشخاص (YOLO)
4. تتبع الأشخاص (Centroid Tracking)
5. كشف الأشياء (laptop, phone, etc.)
6. حساب الحركة (motion level)
7. تحديد النشاط (Rules)
8. تسجيل النشاط مع الوقت
9. دمج المسارات المكررة
10. حساب المدد
```

---

## 🤖 قواعد كشف الأنشطة (بالترتيب)

### 1️⃣ كمبيوتر قريب → Working 💼
```python
if laptop/keyboard/monitor قريب (< 300 بكسل):
    return 'working', 0.9
```

### 2️⃣ هاتف قريب → On Phone 📱
```python
if phone قريب (< 300 بكسل):
    return 'on_phone', 0.85
```

### 3️⃣ حركة قليلة جداً → Sleeping 😴
```python
if motion_level < 0.005:  # ثابت تماماً
    return 'sleeping', 0.8
```

### 4️⃣ حركة قليلة/متوسطة → Working (Default) 💼
```python
if motion_level < 0.1:
    return 'working', 0.6  # الافتراض الأساسي = عمل
```

### 5️⃣ غير ذلك → Unknown ❓
```python
return 'unknown', 0.0
```

---

## 📊 حساب الحركة (Motion Level)

```python
# 1. حساب إزاحة مركز الصندوق
displacement = sqrt((x_new - x_old)² + (y_new - y_old)²)

# 2. التطبيع بقطر الصندوق
diagonal = sqrt(width² + height²)

# 3. حساب motion_level
motion_level = (displacement / diagonal) / time_diff
```

**التفسير:**
- `< 0.005` → ثابت تماماً (نائم)
- `< 0.1` → حركة قليلة (يعمل)
- `> 0.1` → حركة كبيرة

---

## ⏱️ حساب المدد

### الطريقة الصحيحة (الحالية):
```python
duration = num_occurrences / fps

# مثال:
# 27 إطار / 25 fps = 1.08 ثانية ✅
```

### الطريقة الخاطئة (القديمة):
```python
duration = last_time - first_time  # ❌ قد يكون = 0!
```

---

## 🔄 التتبع ودمج المسارات

### إعدادات التتبع:
```python
PersonTracker(
    max_distance=150.0,    # المسافة القصوى (بدلاً من 35)
    max_disappeared=90     # الإطارات قبل الحذف (بدلاً من 60)
)
```

### دمج المسارات المكررة:
```python
# إذا كُشف شخصين (ID=1, ID=2)
# يتم دمجهما في شخص واحد (ID=1)
# الأنشطة تُدمج وتُرتب حسب الوقت
```

---

## ⚙️ الإعدادات المهمة

### المعالج:
```python
SimpleVideoProcessor(
    device="cpu",
    imgsz=640,
    conf_threshold=0.5,
    enable_activity_recognition=True
)
```

### المعالجة:
```python
process_video(
    frame_skip=2,        # معالجة كل إطار ثاني
    max_duration=30      # الحد الأقصى 30 ثانية
)
```

### Thresholds:
```python
# كشف الأشخاص
person_conf = 0.45

# كشف الأشياء
object_conf = 0.25

# المسافة القصوى للأشياء
max_distance = 300 بكسل

# حد النوم
sleeping_threshold = 0.005

# حد العمل
working_threshold = 0.1
```

---

## 🎯 مثال سريع

### الفيديو:
- 2 ثانية، 25 fps، 50 إطار
- frame_skip=2 → 25 إطار معالج

### المعالجة:
```
الإطار 0 (0.00s): كشف شخص + laptop قريب → working
الإطار 2 (0.08s): نفس الشخص + laptop → working
...
الإطار 48 (1.92s): نفس الشخص + laptop → working
```

### النتيجة:
```json
{
    "total_persons": 1,
    "statistics": [{
        "working_duration": 1.0,  // 25 إطار / 25 fps
        "sleeping_duration": 0.0,
        "phone_duration": 0.0,
        "duration": 1.0,
        "top_activity": "working"
    }]
}
```

---

## 🐛 المشاكل الشائعة

| المشكلة | السبب | الحل |
|---------|-------|------|
| المدة = 0 | حساب خاطئ | استخدام `num / fps` ✅ |
| شخصين بدلاً من 1 | فقدان track | زيادة `max_distance` + دمج |
| كل شيء "sleeping" | threshold عالي | تقليل إلى 0.005 |
| لا يكتشف laptop | conf عالي | استخدام 0.25 |

---

## 📈 تدفق البيانات المبسط

```
Video → Frames → Person Detection → Tracking
                                      ↓
                              Object Detection
                                      ↓
                              Motion Calculation
                                      ↓
                              Activity Detection
                                      ↓
                              Duration Calculation
                                      ↓
                                   Results
```

---

## 🎓 النقاط الأساسية

### ✅ ما يعمل جيداً:
- كشف الأشخاص (90-95%)
- التتبع مع الإعدادات الجديدة
- كشف "working" مع laptop
- حساب المدد الجديد

### ⚠️ القيود:
- يحتاج إضاءة جيدة
- يعمل أفضل مع كاميرا ثابتة
- دقة "sleeping" محدودة (70-80%)
- يفضل وجود laptop/keyboard في الفيديو

### 🚀 التحسينات المقترحة:
- استخدام Pose Estimation
- كشف اتجاه الوجه
- نموذج Deep Learning مخصص
- استخدام DeepSORT للتتبع

---

## 📝 الملخص في 3 نقاط

1. **الكشف:** YOLO يكتشف الأشخاص والأشياء
2. **القواعد:** laptop قريب = working، حركة قليلة جداً = sleeping، الافتراض = working
3. **الحساب:** المدة = عدد الإطارات / fps

---

**للتفاصيل الكاملة:** راجع `ACTIVITY_RECOGNITION_STRATEGY.md`

**تاريخ التحديث:** 10 نوفمبر 2025  
**الإصدار:** 2.0
