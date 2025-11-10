# 🗺️ خطة تطوير نظام التعرف على الأنشطة
## Development Roadmap

---

## 📊 نظرة عامة

### الوضع الحالي
- ✅ النظام الأساسي يعمل
- ✅ دقة: 70-80%
- ⚠️ مشاكل في التتبع
- ⚠️ دقة "sleeping" منخفضة

### الهدف
- 🎯 دقة: 90-95%
- 🎯 تتبع مستقر
- 🎯 كشف دقيق للنوم

### المدة
**8-10 أسابيع** (4 مراحل)

---

# 🚀 المرحلة 1: DeepSORT Integration
**المدة:** 1 أسبوع | **الأولوية:** عالية جداً

## الهدف
استبدال Centroid Tracker بـ DeepSORT

## النتيجة المتوقعة
- دقة التتبع: 80% → 95%
- تقليل فقدان ID: 90%
- تحسين الدقة: +5-8%

## الخطوات

### 1. التحضير (يوم 1-2)
```bash
# التثبيت
pip install deep-sort-realtime torch torchvision

# قراءة Documentation
# https://github.com/levan92/deep_sort_realtime
```

### 2. إنشاء Wrapper (يوم 3-4)
**ملف جديد:** `src/deep_sort_tracker.py`

```python
from deep_sort_realtime.deepsort_tracker import DeepSort

class DeepSortTracker:
    def __init__(self, max_age=90, n_init=3):
        self.tracker = DeepSort(
            max_age=max_age,
            n_init=n_init,
            embedder="mobilenet",
            embedder_gpu=False
        )
    
    def update(self, detections, frame):
        # تحويل detections لصيغة DeepSORT
        raw_dets = []
        for det in detections:
            x1, y1, x2, y2 = det['box']
            raw_dets.append(([x1, y1, x2-x1, y2-y1], det['confidence'], 'person'))
        
        # Update
        tracks = self.tracker.update_tracks(raw_dets, frame=frame)
        
        # تحويل النتائج
        result = {}
        for track in tracks:
            if track.is_confirmed():
                ltrb = track.to_ltrb()
                result[track.track_id] = {
                    'box': (int(ltrb[0]), int(ltrb[1]), int(ltrb[2]), int(ltrb[3])),
                    'confidence': 0.8
                }
        return result
```

### 3. التعديلات (يوم 4)
في `simple_video_processor.py`:

```python
# الاستيراد
from src.deep_sort_tracker import DeepSortTracker

# التهيئة
if not self.detection_only:
    self.tracker = DeepSortTracker(max_age=90, n_init=3)

# الاستخدام
tracked_persons = list(self.tracker.update(detections, frame).items())
```

### 4. الاختبار (يوم 5-6)
```python
# مقارنة Centroid vs DeepSORT
# - عدد الأشخاص
# - استقرار ID
# - وقت المعالجة
```

### 5. الضبط (يوم 7)
```python
# جرب إعدادات مختلفة
configs = [
    {'max_age': 90, 'n_init': 3},  # متوازن
    {'max_age': 60, 'n_init': 5},  # صارم
    {'max_age': 120, 'n_init': 2}, # مرن
]
```

## معايير النجاح
- [ ] يعمل بدون أخطاء
- [ ] عدد أشخاص أقل (أقل تكرار)
- [ ] وقت معالجة مقبول (<1.5x)

---

# 🎨 المرحلة 2: Motion Smoothing
**المدة:** 1 أسبوع | **الأولوية:** عالية

## الهدف
تحسين حساب الحركة

## النتيجة المتوقعة
- تقليل False Positives
- انتقالات أكثر سلاسة
- دقة: +3-5%

## الخطوات

### 1. فهم المشكلة (يوم 1)
```python
# المشكلة: إطار واحد قد يحتوي قفزة وهمية
# الحل: متوسط آخر N إطارات
```

### 2. التطبيق (يوم 2-4)
في `simple_activity_detector.py`:

```python
from collections import deque
import numpy as np

class SimpleActivityDetector:
    def __init__(self, motion_window=5):
        self.motion_window = motion_window
        self.motion_history = {}  # {track_id: deque([...])}
    
    def _calculate_motion(self, track_id, box, time):
        # حساب raw motion
        raw_motion = self._calc_raw(track_id, box, time)
        
        # إضافة للـ buffer
        if track_id not in self.motion_history:
            self.motion_history[track_id] = deque(maxlen=self.motion_window)
        self.motion_history[track_id].append(raw_motion)
        
        # حساب المتوسط
        return np.mean(list(self.motion_history[track_id]))
```

### 3. الاختبار (يوم 5-6)
```python
# مقارنة الطرق:
# 1. Simple Moving Average (SMA)
# 2. Exponential Moving Average (EMA)
# 3. Weighted Moving Average (WMA)

# اختر الأفضل
```

## معايير النجاح
- [ ] أقل تذبذب في النشاط
- [ ] دقة أعلى في sleeping
- [ ] لا بطء كبير

---

# 🧘 المرحلة 3: MediaPipe Pose
**المدة:** 2 أسبوع | **الأولوية:** متوسطة

## الهدف
إضافة Pose Estimation لكشف دقيق للنوم

## النتيجة المتوقعة
- دقة sleeping: +10-15%
- كشف اتجاه الرأس
- دقة إجمالية: +7-10%

## الخطوات

### الأسبوع 1: التحضير والتطبيق

#### 1. التثبيت (يوم 1)
```bash
pip install mediapipe opencv-python
```

#### 2. إنشاء Pose Detector (يوم 2-3)
**ملف جديد:** `src/pose_detector.py`

```python
import mediapipe as mp
import numpy as np

class PoseDetector:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.5
        )
    
    def detect(self, frame, person_box):
        """كشف keypoints للشخص"""
        x1, y1, x2, y2 = person_box
        person_crop = frame[y1:y2, x1:x2]
        
        results = self.pose.process(person_crop)
        if results.pose_landmarks:
            return self._extract_keypoints(results.pose_landmarks)
        return None
    
    def _extract_keypoints(self, landmarks):
        """استخراج النقاط المهمة"""
        keypoints = {}
        # الرأس
        keypoints['nose'] = (landmarks.landmark[0].x, landmarks.landmark[0].y)
        keypoints['left_eye'] = (landmarks.landmark[2].x, landmarks.landmark[2].y)
        keypoints['right_eye'] = (landmarks.landmark[5].x, landmarks.landmark[5].y)
        # الأكتاف
        keypoints['left_shoulder'] = (landmarks.landmark[11].x, landmarks.landmark[11].y)
        keypoints['right_shoulder'] = (landmarks.landmark[12].x, landmarks.landmark[12].y)
        return keypoints
    
    def analyze_pose(self, keypoints):
        """تحليل الوضعية"""
        if keypoints is None:
            return None
        
        # حساب زاوية الرأس
        head_angle = self._calculate_head_angle(keypoints)
        
        # تحديد الوضعية
        if head_angle < -30:
            return 'sleeping'  # رأس مائل
        elif -10 < head_angle < 10:
            return 'working'   # رأس للأمام
        else:
            return 'unknown'
    
    def _calculate_head_angle(self, keypoints):
        """حساب زاوية الرأس"""
        nose = keypoints['nose']
        left_shoulder = keypoints['left_shoulder']
        right_shoulder = keypoints['right_shoulder']
        
        # حساب مركز الأكتاف
        shoulder_center_y = (left_shoulder[1] + right_shoulder[1]) / 2
        
        # الزاوية = الفرق بين الأنف ومركز الأكتاف
        angle = np.degrees(np.arctan2(nose[1] - shoulder_center_y, 1))
        return angle
```

#### 3. الدمج (يوم 4-5)
في `simple_activity_detector.py`:

```python
from src.pose_detector import PoseDetector

class SimpleActivityDetector:
    def __init__(self, use_pose=True):
        self.use_pose = use_pose
        if use_pose:
            self.pose_detector = PoseDetector()
    
    def detect_activity(self, person_box, track_id, yolo_detections, frame_time, frame=None):
        # القواعد الحالية...
        
        # إضافة Pose
        if self.use_pose and frame is not None:
            keypoints = self.pose_detector.detect(frame, person_box)
            pose_activity = self.pose_detector.analyze_pose(keypoints)
            
            # إذا Pose يقول sleeping + حركة قليلة → sleeping بثقة عالية
            if pose_activity == 'sleeping' and motion_level < 0.01:
                return 'sleeping', 0.95
        
        # بقية القواعد...
```

### الأسبوع 2: التحسين والاختبار

#### 4. تحسينات إضافية (يوم 6-8)
```python
# إضافة تحليلات أخرى:
# - اتجاه الوجه (face direction)
# - وضعية اليدين (hands position)
# - استقامة الظهر (back straightness)
```

#### 5. الاختبار المكثف (يوم 9-10)
```python
# اختبار على فيديوهات متنوعة:
# - أشخاص نائمون فعلاً
# - أشخاص يعملون
# - إضاءة مختلفة
# - زوايا مختلفة
```

## معايير النجاح
- [ ] يعمل على CPU بسرعة معقولة
- [ ] دقة sleeping أعلى من 85%
- [ ] لا false positives كثيرة

---

# ✨ المرحلة 4: التحسينات النهائية
**المدة:** 2 أسبوع | **الأولوية:** متوسطة-منخفضة

## الهدف
تحسينات متنوعة ورفع الجودة

## المهام

### الأسبوع 1: تحسينات الأداء

#### 1. Optimization (يوم 1-3)
```python
# - تقليل حجم الإطارات المعالجة
# - Multi-threading للكشف
# - Caching للنماذج
```

#### 2. معالجة Edge Cases (يوم 4-5)
```python
# - أكثر من شخص في الكادر
# - إضاءة ضعيفة جداً
# - كاميرا متحركة
# - انسداد جزئي (occlusion)
```

### الأسبوع 2: التوثيق والنشر

#### 3. Documentation (يوم 6-8)
```markdown
# - API Documentation
# - User Guide
# - Examples
# - Troubleshooting
```

#### 4. Testing Suite (يوم 9-10)
```python
# - Unit Tests
# - Integration Tests
# - Performance Tests
```

---

## 📈 جدول التقدم

| المرحلة | المدة | البداية | النهاية | الدقة المتوقعة |
|---------|-------|---------|---------|----------------|
| المرحلة 1: DeepSORT | 1 أسبوع | الأسبوع 1 | الأسبوع 1 | 75-83% |
| المرحلة 2: Motion Smoothing | 1 أسبوع | الأسبوع 2 | الأسبوع 2 | 78-88% |
| المرحلة 3: MediaPipe Pose | 2 أسبوع | الأسبوع 3 | الأسبوع 4 | 85-92% |
| المرحلة 4: التحسينات | 2 أسبوع | الأسبوع 5 | الأسبوع 6 | 90-95% |

---

## 🎯 KPIs لكل مرحلة

### المرحلة 1 (DeepSORT)
- **Metric:** عدد فقدان ID
- **هدف:** < 5% من الإطارات
- **قياس:** `num_id_switches / total_frames`

### المرحلة 2 (Motion Smoothing)
- **Metric:** استقرار النشاط
- **هدف:** < 3 تغييرات/ثانية
- **قياس:** `activity_changes / video_duration`

### المرحلة 3 (Pose)
- **Metric:** دقة sleeping
- **هدف:** > 85%
- **قياس:** `true_positives / (true_positives + false_positives)`

### المرحلة 4 (النهائي)
- **Metric:** الدقة الإجمالية
- **هدف:** > 90%
- **قياس:** `correct_classifications / total_classifications`

---

## 🔧 الأدوات المطلوبة

```bash
# المرحلة 1
pip install deep-sort-realtime torch torchvision

# المرحلة 2
pip install numpy scipy

# المرحلة 3
pip install mediapipe

# المرحلة 4
pip install pytest black flake8
```

---

## 📝 ملاحظات مهمة

### 1. الأولويات
- **يجب:** DeepSORT + Motion Smoothing
- **مهم:** MediaPipe Pose
- **اختياري:** التحسينات الإضافية

### 2. المرونة
- كل مرحلة مستقلة
- يمكن تخطي المرحلة 4
- يمكن تبديل ترتيب المراحل 2 و 3

### 3. القياسات
- قس الأداء بعد كل مرحلة
- احتفظ بـ baseline للمقارنة
- وثق كل التغييرات

---

## 🚀 البدء

### الخطوة التالية المباشرة:
```bash
# 1. إنشاء branch جديد
git checkout -b feature/deepsort-integration

# 2. تثبيت المكتبات
pip install deep-sort-realtime

# 3. إنشاء ملف tracker جديد
touch src/deep_sort_tracker.py

# 4. البدء في الكود!
```

---

**تاريخ الإنشاء:** 10 نوفمبر 2025  
**آخر تحديث:** 10 نوفمبر 2025  
**الحالة:** جاهز للتنفيذ ✅
