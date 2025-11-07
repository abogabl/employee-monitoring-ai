# 📹 دليل إضافة كاميرا جديدة

## 🎯 طرق إضافة الكاميرات

هناك **3 طرق** لإضافة كاميرا:

1. **عبر تطبيق الويب** (الأسهل) ✅
2. **تعديل ملف التكوين يدوياً**
3. **عبر سطر الأوامر**

---

## 🌐 الطريقة 1: عبر تطبيق الويب (الأسهل)

### الخطوات:

1. **افتح تطبيق الويب**
   ```
   http://127.0.0.1:8080
   ```

2. **سجّل الدخول كـ admin**
   - اسم المستخدم: `admin`
   - كلمة المرور: `admin`

3. **اذهب لصفحة الكاميرات**
   - من القائمة العلوية → الكاميرات

4. **اضغط "إضافة كاميرا جديدة"** أو "تعديل الإعدادات"

5. **أضف تكوين الكاميرا:**

   ```json
   {
     "cameras": [
       {
         "camera_id": "cam_01",
         "name": "كاميرا المدخل",
         "source": 0,
         "enabled": true,
         "fps": 30
       },
       {
         "camera_id": "cam_02",
         "name": "كاميرا المكتب",
         "source": "rtsp://192.168.1.100:554/stream",
         "enabled": true,
         "fps": 25
       }
     ]
   }
   ```

6. **احفظ الإعدادات**

7. **ابدأ الكاميرا**
   - اضغط زر "تشغيل" بجانب الكاميرا الجديدة

---

## 📝 الطريقة 2: تعديل ملف التكوين يدوياً

### الخطوات:

1. **افتح الملف:**
   ```
   config/cameras_config.json
   ```

2. **أضف الكاميرا الجديدة:**

   ```json
   {
     "cameras": [
       {
         "camera_id": "cam_01",
         "name": "كاميرا المدخل الرئيسي",
         "source": 0,
         "enabled": true,
         "fps": 30,
         "resolution": [1280, 720],
         "detection_zone": null,
         "roi": null
       },
       {
         "camera_id": "cam_02",
         "name": "كاميرا المكتب الأول",
         "source": "rtsp://admin:pass123@192.168.1.100:554/stream1",
         "enabled": true,
         "fps": 25,
         "resolution": [1920, 1080]
       },
       {
         "camera_id": "cam_03",
         "name": "كاميرا الممر",
         "source": "http://192.168.1.101/video.mjpeg",
         "enabled": true,
         "fps": 20
       }
     ]
   }
   ```

3. **احفظ الملف**

4. **أعد تشغيل التطبيق**

---

## 🎥 أنواع مصادر الكاميرات المدعومة

### 1. كاميرا USB/Webcam

```json
{
  "camera_id": "usb_cam",
  "source": 0,
  "name": "كاميرا USB"
}
```

- `0` = الكاميرا الأولى
- `1` = الكاميرا الثانية
- `2` = الكاميرا الثالثة... وهكذا

### 2. كاميرا RTSP

```json
{
  "camera_id": "rtsp_cam",
  "source": "rtsp://username:password@192.168.1.100:554/stream",
  "name": "كاميرا IP"
}
```

**أمثلة شائعة:**

#### Hikvision:
```
rtsp://admin:password@192.168.1.64:554/Streaming/Channels/101
```

#### Dahua:
```
rtsp://admin:password@192.168.1.108:554/cam/realmonitor?channel=1&subtype=0
```

#### TP-Link:
```
rtsp://admin:password@192.168.1.100:554/stream1
```

#### Generic:
```
rtsp://username:password@IP:PORT/stream
```

### 3. كاميرا HTTP/MJPEG

```json
{
  "camera_id": "http_cam",
  "source": "http://192.168.1.100/video.mjpeg",
  "name": "كاميرا HTTP"
}
```

### 4. ملف فيديو

```json
{
  "camera_id": "video_file",
  "source": "videos/test.mp4",
  "name": "ملف تجريبي"
}
```

### 5. رابط YouTube أو Stream آخر

```json
{
  "camera_id": "stream",
  "source": "https://example.com/live/stream.m3u8",
  "name": "بث مباشر"
}
```

---

## ⚙️ الإعدادات المتقدمة

### مثال كامل مع كل الخيارات:

```json
{
  "camera_id": "office_main",
  "name": "المكتب الرئيسي - الطابق الثاني",
  "source": "rtsp://admin:pass@192.168.1.100:554/stream",
  "enabled": true,
  "fps": 25,
  "resolution": [1920, 1080],
  "detection_zone": {
    "x1": 100,
    "y1": 100,
    "x2": 1800,
    "y2": 900
  },
  "roi": [
    [200, 200],
    [1700, 200],
    [1700, 800],
    [200, 800]
  ],
  "record": true,
  "record_path": "recordings/office_main",
  "alert_enabled": true,
  "motion_detection": true
}
```

### شرح المعاملات:

| المعامل | الوصف | مطلوب؟ | مثال |
|---------|-------|--------|------|
| `camera_id` | معرف فريد للكاميرا | ✅ نعم | `"cam_01"` |
| `name` | اسم وصفي | ✅ نعم | `"كاميرا المدخل"` |
| `source` | مصدر الكاميرا | ✅ نعم | `0` أو `"rtsp://..."` |
| `enabled` | هل مفعّلة؟ | ❌ لا | `true` |
| `fps` | الإطارات بالثانية | ❌ لا | `25` |
| `resolution` | الدقة [عرض، ارتفاع] | ❌ لا | `[1920, 1080]` |
| `detection_zone` | منطقة الكشف | ❌ لا | `{x1, y1, x2, y2}` |
| `roi` | منطقة الاهتمام | ❌ لا | نقاط متعددة |
| `record` | هل نسجل؟ | ❌ لا | `true` |
| `record_path` | مسار التسجيل | ❌ لا | `"recordings/"` |

---

## 🖥️ الطريقة 3: عبر سطر الأوامر

### لكاميرا واحدة:

```bash
python src/main_production.py \
    --source 0 \
    --enable-face-recognition \
    --enable-activity-recognition \
    --display
```

### لكاميرات متعددة:

```bash
python run_multi_camera.py
```

سيقرأ التكوين من `config/cameras_config.json` تلقائياً.

---

## 🔍 اختبار الكاميرا

### اختبار سريع:

```bash
python -c "import cv2; cap = cv2.VideoCapture(0); print('OK' if cap.isOpened() else 'FAIL'); cap.release()"
```

**للكاميرا USB:**
```bash
python -c "import cv2; cap = cv2.VideoCapture(0); print(cap.isOpened())"
```

**للكاميرا RTSP:**
```bash
python -c "import cv2; cap = cv2.VideoCapture('rtsp://192.168.1.100:554/stream'); print(cap.isOpened())"
```

### اختبار مع عرض:

```python
# test_camera.py
import cv2

source = 0  # غيّر هذا لكاميرتك
cap = cv2.VideoCapture(source)

if not cap.isOpened():
    print("❌ فشل فتح الكاميرا!")
    exit()

print("✅ الكاميرا تعمل! اضغط 'q' للخروج")

while True:
    ret, frame = cap.read()
    if not ret:
        print("❌ فشل قراءة الإطار")
        break
    
    cv2.imshow("Camera Test", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

---

## 🐛 حل المشاكل الشائعة

### المشكلة: "Cannot open camera"

**الحلول:**
1. تحقق من الرقم الصحيح للكاميرا (0, 1, 2...)
2. تأكد أن الكاميرا ليست مستخدمة من برنامج آخر
3. تحقق من توصيل USB

### المشكلة: "RTSP stream failed"

**الحلول:**
1. تحقق من الـ IP والـ Port
2. تحقق من اسم المستخدم وكلمة المرور
3. تحقق من المسار `/stream` أو `/Streaming/Channels/101`
4. جرب VLC أولاً لاختبار الرابط:
   ```
   vlc rtsp://admin:pass@192.168.1.100:554/stream
   ```

### المشكلة: "Camera lag/freeze"

**الحلول:**
1. قلل الـ FPS في التكوين:
   ```json
   "fps": 15
   ```
2. قلل الدقة:
   ```json
   "resolution": [1280, 720]
   ```
3. استخدم `opencv-python-headless` بدلاً من `opencv-python`

### المشكلة: "Multiple cameras not working"

**الحلول:**
1. تأكد من أن كل كاميرا لها `camera_id` فريد
2. قلل الـ FPS لكل الكاميرات
3. استخدم نظام متعدد العمليات:
   ```bash
   python run_multi_camera.py
   ```

---

## 📊 أمثلة واقعية

### مثال 1: مكتب صغير (3 كاميرات)

```json
{
  "cameras": [
    {
      "camera_id": "entrance",
      "name": "المدخل",
      "source": 0,
      "enabled": true,
      "fps": 25
    },
    {
      "camera_id": "office_1",
      "name": "المكتب الأول",
      "source": "rtsp://admin:pass@192.168.1.101:554/stream",
      "enabled": true,
      "fps": 25
    },
    {
      "camera_id": "hall",
      "name": "الصالة",
      "source": "rtsp://admin:pass@192.168.1.102:554/stream",
      "enabled": true,
      "fps": 20
    }
  ]
}
```

### مثال 2: شركة كبيرة (10+ كاميرات)

```json
{
  "cameras": [
    {
      "camera_id": "floor1_entrance",
      "name": "الطابق الأول - المدخل",
      "source": "rtsp://admin:pass@192.168.1.101:554/stream",
      "enabled": true,
      "fps": 25,
      "detection_zone": {"x1": 200, "y1": 200, "x2": 1720, "y2": 880}
    },
    {
      "camera_id": "floor1_hall",
      "name": "الطابق الأول - الصالة",
      "source": "rtsp://admin:pass@192.168.1.102:554/stream",
      "enabled": true,
      "fps": 20
    },
    {
      "camera_id": "floor2_office_a",
      "name": "الطابق الثاني - مكتب A",
      "source": "rtsp://admin:pass@192.168.1.201:554/stream",
      "enabled": true,
      "fps": 20
    }
    // ... المزيد من الكاميرات
  ]
}
```

---

## 🎯 الخلاصة السريعة

### لإضافة كاميرا جديدة:

1. ✅ حدد نوع المصدر (USB, RTSP, HTTP, ملف)
2. ✅ احصل على الرابط أو الرقم
3. ✅ اختبر الكاميرا أولاً
4. ✅ أضفها في `config/cameras_config.json`
5. ✅ شغّل التطبيق

### الأسهل:
استخدم تطبيق الويب → الكاميرات → إضافة كاميرا ✅

---

**جاهز لإضافة كاميراتك! 📹**
