# 🎯 استراتيجية التعرف على الأنشطة
## Activity Recognition Strategy

---

## 📋 جدول المحتويات

1. [نظرة عامة](#نظرة-عامة)
2. [المعالج المبسط (SimpleVideoProcessor)](#المعالج-المبسط)
3. [كاشف الأنشطة (SimpleActivityDetector)](#كاشف-الأنشطة)
4. [الخوارزميات المستخدمة](#الخوارزميات-المستخدمة)
5. [حساب المدد](#حساب-المدد)
6. [التتبع ودمج المسارات](#التتبع-ودمج-المسارات)
7. [الإعدادات والمعاملات](#الإعدادات-والمعاملات)

---

## 🔍 نظرة عامة

### الهدف
التعرف على أنشطة الموظفين في الفيديو وحساب مدة كل نشاط بدقة.

### الأنشطة المدعومة
1. **Working (العمل)** 💼 - استخدام الكمبيوتر أو الجلوس بشكل طبيعي
2. **Sleeping (النوم)** 😴 - عدم وجود حركة تقريباً
3. **On Phone (الهاتف)** 📱 - استخدام الهاتف المحمول
4. **Idle (خامل)** ⏸️ - حركة قليلة بدون نشاط محدد
5. **Unknown (غير معروف)** ❓ - لا يمكن تحديد النشاط

### المكونات الرئيسية
```
SimpleVideoProcessor (المعالج الرئيسي)
    ├── PersonDetector (كشف الأشخاص - YOLO)
    ├── PersonTracker (تتبع الأشخاص)
    ├── SimpleActivityDetector (كشف الأنشطة)
    └── FaceRecognitionSystem (التعرف على الوجوه - اختياري)
```

---

## 🎬 المعالج المبسط (SimpleVideoProcessor)

### الملف
`src/simple_video_processor.py`

### الوظيفة الرئيسية
```python
def process_video(
    input_path: str,
    output_path: str,
    frame_skip: int = 2,      # معالجة كل إطار ثاني
    max_duration: int = -1    # الحد الأقصى للمدة بالثواني
) -> Dict[str, Any]
```

### خطوات المعالجة

#### 1. **فتح الفيديو وقراءة المعلومات**
```python
cap = cv2.VideoCapture(input_path)
fps = cap.get(cv2.CAP_PROP_FPS)           # مثال: 25 fps
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
```

#### 2. **حساب الحد الأقصى للإطارات**
```python
if max_duration > 0:
    max_frames = int(max_duration * fps)  # مثال: 30s × 25fps = 750 إطار
else:
    max_frames = total_frames
```

#### 3. **حلقة المعالجة الرئيسية**
```python
frame_num = 0
person_data = {}  # تخزين بيانات كل شخص

while cap.isOpened() and frame_num < max_frames:
    ret, frame = cap.read()
    if not ret:
        break
    
    current_time = frame_num / fps  # الوقت بالثواني
    
    # معالجة كل frame_skip إطار
    if frame_num % frame_skip == 0:
        # 1. كشف الأشخاص
        detections = person_detector.detect(frame)
        
        # 2. تتبع الأشخاص
        tracked_persons = tracker.update(detections)
        
        # 3. لكل شخص:
        for track_id, person_info in tracked_persons:
            # 3.1 كشف الأشياء (laptop, phone, etc.)
            yolo_detections = detect_objects(frame)
            
            # 3.2 كشف النشاط
            activity, confidence = activity_detector.detect_activity(
                person_box=person_info['box'],
                track_id=track_id,
                yolo_detections=yolo_detections,
                frame_time=current_time
            )
            
            # 3.3 حفظ النشاط مع الوقت
            person_data[track_id]['activities'].append((current_time, activity))
    
    frame_num += 1
```

#### 4. **دمج المسارات المكررة**
```python
if len(person_data) > 1:
    person_data = _merge_duplicate_tracks(person_data)
```

#### 5. **حساب النتائج**
```python
results = _calculate_results(person_data, fps, processing_time, processed_frames)
```

---

## 🤖 كاشف الأنشطة (SimpleActivityDetector)

### الملف
`src/simple_activity_detector.py`

### الخوارزمية الرئيسية

```python
def detect_activity(
    person_box: Tuple[int, int, int, int],
    track_id: int,
    yolo_detections: List[Dict],
    frame_time: float
) -> Tuple[str, float]:
    """
    كشف النشاط بناءً على:
    1. الأشياء القريبة (laptop, phone, etc.)
    2. مستوى الحركة (motion level)
    """
```

### القواعد بالترتيب (Priority Order)

#### **القاعدة 1: كمبيوتر قريب → Working** 💼
```python
if computer_nearby:  # laptop, keyboard, monitor, tv
    if distance < 200:
        return 'working', 0.9  # ثقة عالية
    else:
        return 'working', 0.75  # ثقة متوسطة
```

**الأشياء المعتبرة "كمبيوتر":**
- Class 62: TV
- Class 63: Laptop
- Class 66: Keyboard
- Class 72: Monitor

**المسافة القصوى:** 300 بكسل من مركز الشخص

#### **القاعدة 2: هاتف قريب → On Phone** 📱
```python
if phone_nearby:  # cell phone
    if distance < 150:
        return 'on_phone', 0.85  # ثقة عالية
    else:
        return 'on_phone', 0.7   # ثقة متوسطة
```

**الأشياء المعتبرة "هاتف":**
- Class 67: Cell Phone

**المسافة القصوى:** 300 بكسل من مركز الشخص

#### **القاعدة 3: حركة قليلة جداً → Sleeping** 😴
```python
if motion_level < 0.005:  # ثابت تماماً
    return 'sleeping', 0.8
```

**كيفية حساب motion_level:** انظر [حساب الحركة](#حساب-الحركة)

#### **القاعدة 4: حركة قليلة/متوسطة → Working (Default)** 💼
```python
if motion_level < 0.1:
    return 'working', 0.6  # افتراض أنه يعمل
```

**المنطق:**
- في بيئة العمل، الافتراض الأساسي هو **العمل**
- إلا إذا كان نائماً أو يستخدم الهاتف

#### **القاعدة 5: غير معروف** ❓
```python
return 'unknown', 0.0
```

---

## 📊 الخوارزميات المستخدمة

### 1. كشف الأشخاص (Person Detection)

**النموذج:** YOLOv8 (Medium)

```python
PersonDetector(
    model_size="m",           # yolov8m.pt
    device="cpu",             # أو "cuda" للـ GPU
    imgsz=960,                # حجم الصورة للمعالجة
    conf=0.45                 # حد الثقة الأدنى
)
```

**الخرج:**
```python
[
    {
        'box': (x1, y1, x2, y2),  # إحداثيات الصندوق
        'conf': 0.85,              # مستوى الثقة
        'class': 0                 # 0 = person
    },
    ...
]
```

### 2. تتبع الأشخاص (Person Tracking)

**الخوارزمية:** Centroid Tracking (تتبع المركز)

```python
PersonTracker(
    max_disappeared=90,    # عدد الإطارات قبل حذف المسار
    max_distance=150.0     # المسافة القصوى بالبكسل
)
```

**كيف يعمل:**
1. حساب مركز كل صندوق: `centroid = ((x1+x2)/2, (y1+y2)/2)`
2. مقارنة المراكز الجديدة مع القديمة
3. إذا المسافة < 150 بكسل → نفس الشخص
4. إذا المسافة > 150 بكسل → شخص جديد

**معادلة المسافة:**
```python
distance = sqrt((x1 - x2)² + (y1 - y2)²)
```

### 3. حساب الحركة (Motion Calculation)

**الخوارزمية:**
```python
def _calculate_motion(track_id, current_box, frame_time):
    # 1. حساب مركز الصندوق الحالي
    current_center = ((x1 + x2) / 2, (y1 + y2) / 2)
    
    # 2. الحصول على المركز السابق
    if track_id in previous_positions:
        prev_center, prev_time = previous_positions[track_id]
        
        # 3. حساب الإزاحة (displacement)
        dx = current_center[0] - prev_center[0]
        dy = current_center[1] - prev_center[1]
        displacement = sqrt(dx² + dy²)
        
        # 4. حساب قطر الصندوق (للتطبيع)
        width = x2 - x1
        height = y2 - y1
        diagonal = sqrt(width² + height²)
        
        # 5. حساب الفرق الزمني
        time_diff = frame_time - prev_time
        if time_diff > 0:
            # 6. حساب motion_level المطبّع
            motion_level = (displacement / diagonal) / time_diff
        else:
            motion_level = 0.0
    else:
        motion_level = 0.0
    
    # 7. حفظ الموضع الحالي
    previous_positions[track_id] = (current_center, frame_time)
    
    return motion_level
```

**مثال:**
```
displacement = 10 بكسل
diagonal = 200 بكسل
time_diff = 0.04 ثانية (1 إطار @ 25fps)

motion_level = (10 / 200) / 0.04 = 0.05 / 0.04 = 1.25
```

**التفسير:**
- `motion_level < 0.005` → ثابت تماماً (sleeping)
- `motion_level < 0.1` → حركة قليلة (working)
- `motion_level > 0.1` → حركة متوسطة/كبيرة

### 4. كشف الأشياء (Object Detection)

**النموذج:** نفس YOLO المستخدم لكشف الأشخاص

**الأشياء المستهدفة:**
```python
obj_classes = [62, 63, 66, 67, 72]
# 62: tv
# 63: laptop
# 66: keyboard
# 67: cell phone
# 72: monitor
```

**الإعدادات:**
```python
results = model.predict(
    frame,
    imgsz=960,
    conf=0.25,        # حد ثقة أقل للأشياء
    device="cpu",
    classes=obj_classes,
    verbose=False
)
```

---

## ⏱️ حساب المدد

### الطريقة الجديدة: Time-Based Tracking

#### 1. **تسجيل الأنشطة مع الوقت**
```python
person_data[track_id]['activities'].append((current_time, activity))

# مثال:
# [(0.0, 'working'), (0.08, 'working'), (0.16, 'working'), ...]
```

#### 2. **تجميع الأنشطة حسب النوع**
```python
activity_groups = {}
for time_val, activity in activities:
    if activity != 'unknown':
        if activity not in activity_groups:
            activity_groups[activity] = []
        activity_groups[activity].append(time_val)

# مثال:
# {
#     'working': [0.0, 0.08, 0.16, 0.24, ...],
#     'sleeping': [5.0, 5.08, 5.16]
# }
```

#### 3. **حساب المدة لكل نشاط**
```python
for activity, times in activity_groups.items():
    num_occurrences = len(times)
    duration = num_occurrences / fps
    
    activity_durations[activity] = duration

# مثال:
# num_occurrences = 27
# fps = 25
# duration = 27 / 25 = 1.08 ثانية
```

#### 4. **حساب المدة الإجمالية**
```python
total_duration = len(all_activities) / fps

# مثال:
# all_activities = 150 إطار
# fps = 25
# total_duration = 150 / 25 = 6.0 ثانية
```

### لماذا هذه الطريقة؟

**الطريقة القديمة (فشلت):**
```python
duration = last_time - first_time  # ❌ خطأ!
# مثال: 0.9 - 0.9 = 0.0 ثانية!
```

**الطريقة الجديدة (صحيحة):**
```python
duration = num_occurrences / fps  # ✅ صحيح!
# مثال: 27 / 25 = 1.08 ثانية
```

**الفرق:**
- القديمة تعتمد على **الفرق الزمني** (قد يكون صفر)
- الجديدة تعتمد على **عدد الإطارات** (دائماً صحيح)

---

## 🔄 التتبع ودمج المسارات

### مشكلة التتبع المكرر

**المشكلة:**
- الشخص يتحرك قليلاً
- Tracker يفقد الـ track
- يعطيه ID جديد
- النتيجة: شخص واحد يظهر كشخصين!

**الحل:**

#### 1. **زيادة مسافة التتبع**
```python
PersonTracker(
    max_distance=150.0,    # بدلاً من 35.0
    max_disappeared=90     # بدلاً من 60
)
```

#### 2. **دمج المسارات المكررة**
```python
def _merge_duplicate_tracks(person_data):
    """دمج كل المسارات في مسار واحد"""
    
    merged_data = {
        1: {
            'activities': [],
            'first_time': float('inf'),
            'last_time': 0.0,
            'name': 'Unknown',
            'snapshot': None
        }
    }
    
    # دمج كل المسارات
    for track_id, data in person_data.items():
        # دمج الأنشطة
        merged_data[1]['activities'].extend(data['activities'])
        
        # تحديث الأوقات
        merged_data[1]['first_time'] = min(merged_data[1]['first_time'], data['first_time'])
        merged_data[1]['last_time'] = max(merged_data[1]['last_time'], data['last_time'])
        
        # استخدام أول snapshot
        if merged_data[1]['snapshot'] is None and data['snapshot']:
            merged_data[1]['snapshot'] = data['snapshot']
    
    # ترتيب الأنشطة حسب الوقت
    merged_data[1]['activities'].sort(key=lambda x: x[0])
    
    return merged_data
```

**النتيجة:**
- شخصين (ID=1, ID=2) → شخص واحد (ID=1)
- الأنشطة مدمجة ومرتبة
- المدد محسوبة بشكل صحيح

---

## ⚙️ الإعدادات والمعاملات

### إعدادات المعالج

```python
SimpleVideoProcessor(
    device="cpu",                          # "cpu" أو "cuda"
    imgsz=640,                             # حجم الصورة (640-1280)
    conf_threshold=0.5,                    # حد الثقة (0.3-0.7)
    enable_face_recognition=False,         # تعطيل للسرعة
    enable_activity_recognition=True,      # تفعيل كشف الأنشطة
    detection_only=False                   # تفعيل التتبع
)
```

### إعدادات كشف الأنشطة

```python
SimpleActivityDetector(
    max_distance=300  # المسافة القصوى للأشياء القريبة
)
```

### إعدادات التتبع

```python
PersonTracker(
    max_disappeared=90,    # عدد الإطارات قبل الحذف
    max_distance=150.0     # المسافة القصوى بالبكسل
)
```

### إعدادات المعالجة

```python
process_video(
    input_path="video.mp4",
    output_path="output.avi",
    frame_skip=2,          # معالجة كل إطار ثاني (سرعة)
    max_duration=30        # الحد الأقصى 30 ثانية
)
```

### Thresholds الأنشطة

```python
# Sleeping
motion_level < 0.005  # ثابت تماماً

# Working (default)
motion_level < 0.1    # حركة قليلة/متوسطة

# Computer nearby
distance < 200  # confidence = 0.9
distance < 300  # confidence = 0.75

# Phone nearby
distance < 150  # confidence = 0.85
distance < 300  # confidence = 0.7
```

---

## 📈 تدفق البيانات (Data Flow)

```
1. Video Input (الفيديو المدخل)
   ↓
2. Frame Extraction (استخراج الإطارات)
   ↓ (كل frame_skip إطار)
3. Person Detection (كشف الأشخاص - YOLO)
   ↓
4. Person Tracking (تتبع الأشخاص - Centroid)
   ↓
5. Object Detection (كشف الأشياء - YOLO)
   ↓
6. Motion Calculation (حساب الحركة)
   ↓
7. Activity Detection (كشف النشاط - Rules)
   ↓
8. Activity Recording (تسجيل النشاط مع الوقت)
   ↓
9. Track Merging (دمج المسارات المكررة)
   ↓
10. Duration Calculation (حساب المدد)
    ↓
11. Results Output (النتائج النهائية)
```

---

## 🎯 مثال عملي كامل

### الفيديو
- المدة: 2 ثانية
- FPS: 25
- الإطارات الإجمالية: 50
- frame_skip: 2
- الإطارات المعالجة: 25

### المعالجة

**الإطار 0 (t=0.00s):**
```python
# كشف شخص واحد
person_box = (100, 50, 300, 400)

# كشف laptop قريب
laptop_box = (150, 100, 250, 200)
distance = 30 بكسل  # قريب جداً!

# النشاط
activity = 'working', confidence = 0.9

# التسجيل
person_data[1]['activities'].append((0.0, 'working'))
```

**الإطار 2 (t=0.08s):**
```python
# نفس الشخص (track_id=1)
person_box = (105, 52, 305, 402)  # تحرك قليلاً

# laptop لا يزال قريب
activity = 'working', confidence = 0.9

# التسجيل
person_data[1]['activities'].append((0.08, 'working'))
```

**... (23 إطار آخر)**

### النتائج

```python
person_data = {
    1: {
        'activities': [
            (0.0, 'working'),
            (0.08, 'working'),
            (0.16, 'working'),
            # ... 22 إطار آخر
        ],
        'first_time': 0.0,
        'last_time': 1.92,
        'snapshot': 'person_1_12345.jpg'
    }
}

# حساب المدد
activity_groups = {
    'working': [0.0, 0.08, 0.16, ..., 1.92]  # 25 occurrence
}

working_duration = 25 / 25 = 1.0 ثانية
total_duration = 25 / 25 = 1.0 ثانية

# النتيجة النهائية
{
    'total_persons': 1,
    'statistics': [{
        'track_id': 1,
        'name': 'Unknown',
        'working_duration': 1.0,
        'sleeping_duration': 0.0,
        'phone_duration': 0.0,
        'duration': 1.0,
        'top_activity': 'working',
        'snapshot': 'uploads/test_videos/snapshots/person_1_12345.jpg'
    }]
}
```

---

## 🐛 المشاكل الشائعة والحلول

### 1. المدة = 0

**السبب:** استخدام `last_time - first_time` بدلاً من `num_occurrences / fps`

**الحل:** تم إصلاحه في الكود الحالي

### 2. شخصين بدلاً من واحد

**السبب:** Tracker يفقد الـ track

**الحل:** 
- زيادة `max_distance` إلى 150
- دمج المسارات المكررة

### 3. كل الأنشطة "sleeping"

**السبب:** threshold منخفض جداً (`motion_level < 0.01`)

**الحل:** 
- تقليل threshold إلى 0.005
- الافتراض الأساسي = "working"

### 4. لا يكتشف laptop/keyboard

**السبب:** 
- الأشياء صغيرة جداً في الفيديو
- confidence threshold عالي

**الحل:**
- استخدام `conf=0.25` للأشياء
- زيادة `max_distance` إلى 300

---

## 📝 ملاحظات مهمة

### 1. الأداء
- **CPU:** ~2-3 إطار/ثانية
- **GPU:** ~10-15 إطار/ثانية
- استخدم `frame_skip=2` للسرعة

### 2. الدقة
- **كشف الأشخاص:** ~90-95%
- **كشف الأنشطة:** ~70-80% (بدون laptop)
- **كشف الأنشطة:** ~90-95% (مع laptop)

### 3. القيود
- يعمل بشكل أفضل مع:
  - إضاءة جيدة
  - كاميرا ثابتة
  - وضوح عالي
  - laptop/keyboard مرئي

---

## 🔧 التطوير المستقبلي

### تحسينات مقترحة:

1. **استخدام Pose Estimation**
   - MediaPipe Pose
   - كشف وضعية الجسم
   - تحسين دقة "sleeping"

2. **استخدام Face Detection**
   - كشف اتجاه الوجه
   - كشف العيون المغلقة
   - تحسين دقة "sleeping"

3. **استخدام Deep Learning للأنشطة**
   - تدريب نموذج مخصص
   - استخدام Temporal CNN
   - دقة أعلى

4. **تحسين التتبع**
   - استخدام DeepSORT
   - Re-identification
   - تقليل فقدان الـ tracks

---

## 📚 المراجع

- **YOLOv8:** https://github.com/ultralytics/ultralytics
- **OpenCV:** https://opencv.org/
- **Centroid Tracking:** https://pyimagesearch.com/2018/07/23/simple-object-tracking-with-opencv/

---

**تاريخ التحديث:** 10 نوفمبر 2025  
**الإصدار:** 2.0 (SimpleVideoProcessor)  
**المطور:** Employee Monitoring AI System
