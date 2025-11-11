# 📑 دليل المشروع الشامل - Project Index

## 🎯 الملفات النشطة (المستخدمة حالياً)

### ⭐ ملفات البدء السريع
| الملف | الوظيفة | الأولوية |
|-------|---------|---------|
| `README_AR.md` | دليل البدء الرئيسي | ⭐⭐⭐ |
| `run_web_app.py` | تشغيل تطبيق الويب | ⭐⭐⭐ |
| `test_enhanced_system.py` | اختبار النظام المحسّن | ⭐⭐⭐ |
| `START_HERE_AR.md` | ابدأ من هنا | ⭐⭐⭐ |

### 📚 وثائق أساسية (نشطة)
| الملف | الوصف |
|-------|--------|
| `PROJECT_STATUS_AR.md` | حالة المشروع |
| `ACCURACY_IMPROVEMENTS_AR.md` | تحسينات الدقة الجديدة |
| `ENHANCEMENTS_SUMMARY_AR.md` | ملخص التحسينات |
| `ADVANCED_RECOMMENDATIONS_AR.md` | توصيات للوصول إلى 95%+ |
| `MODELS_SUMMARY_AR.md` | ملخص النماذج المستخدمة |
| `ADMIN_GUIDE_AR.md` | دليل المسؤول |
| `ADD_NEW_EMPLOYEE_GUIDE_AR.md` | دليل إضافة موظف |
| `ADD_CAMERA_GUIDE_AR.md` | دليل إضافة كاميرا |

### 🚀 سكريبتات التشغيل (نشطة)
| الملف | الوظيفة |
|-------|---------|
| `run_web_app.py` | تشغيل الواجهة الويب |
| `run_multi_camera.py` | تشغيل نظام الكاميرات |
| `train_faces.py` | تدريب التعرف على الوجوه |
| `add_employee.py` | إضافة موظف جديد |
| `generate_report.py` | إنشاء التقارير |
| `test_enhanced_system.py` | اختبار النظام المحسّن |
| `run_tests.py` | تشغيل جميع الاختبارات |

### 💻 الكود المصدري الأساسي (src/)
| الملف | الوظيفة | الحالة |
|-------|---------|--------|
| `advanced_activity_detector.py` | كاشف أنشطة محسّن (85%+) | ⭐ جديد |
| `enhanced_face_recognition.py` | تعرف وجوه محسّن (90%+) | ⭐ جديد |
| `detection_tracking.py` | كشف وتتبع YOLO | نشط |
| `face_recognition_system.py` | نظام التعرف على الوجوه | نشط |
| `multi_camera_runner.py` | إدارة عدة كاميرات | نشط |
| `attendance_system.py` | نظام الحضور والانصراف | نشط |
| `reporting.py` | نظام التقارير | نشط |
| `cross_camera_tracker.py` | تتبع بين الكاميرات | نشط |
| `reid.py` | Re-identification | نشط |
| `alert_system.py` | نظام التنبيهات | نشط |
| `activity_recognition.py` | كشف الأنشطة الأساسي | نشط |
| `activity_rules.py` | قواعد الأنشطة | نشط |
| `simple_activity_detector.py` | كاشف بسيط (للمقارنة) | نشط |
| `simple_video_processor.py` | معالج الفيديو | نشط |

### 🌐 تطبيق الويب (web_app/)
| الملف/المجلد | الوظيفة |
|--------------|---------|
| `app.py` | التطبيق الرئيسي |
| `auth.py` | نظام المصادقة والصلاحيات |
| `api.py` | API endpoints |
| `templates/` | قوالب HTML |
| `static/` | CSS, JS, Images |

---

## 📦 الملفات المؤرشفة (archive_old_files/)

### 🗄️ ما تم نقله وسبب النقل

#### سكريبتات قديمة تم استبدالها:
| الملف | السبب | البديل |
|-------|-------|--------|
| `test_activities.py` | قديم | `test_enhanced_system.py` |
| `test_detection.py` | قديم | `test_enhanced_system.py` |
| `test_face_recognition.py` | قديم | `test_enhanced_system.py` |
| `alert_monitor.py` | مدمج في النظام | `src/alert_system.py` |
| `attendance_dashboard.py` | مدمج في web_app | `web_app/app.py` |
| `auto_report_scheduler.py` | مدمج | `src/reporting.py` |
| `compliance_check.py` | قديم | - |
| `daily_maintenance.py` | قديم | - |
| `export_attendance.py` | مدمج | `generate_report.py` |
| `show_final_report.py` | مدمج | `web_app/` |
| `performance_config.json` | قديم | `config.json` |

#### وثائق قديمة/مكررة (old_docs/):
| الملف | السبب | البديل |
|-------|-------|--------|
| `ACTIVITY_RECOGNITION_STRATEGY.md` | مكرر | `ACCURACY_IMPROVEMENTS_AR.md` |
| `ACTIVITY_RECOGNITION_SUMMARY.md` | مكرر | `ENHANCEMENTS_SUMMARY_AR.md` |
| `ACTIVITY_TRACKING_EXPLAINED_AR.md` | مكرر | `MODELS_SUMMARY_AR.md` |
| `DEVELOPMENT_ROADMAP.md` | قديم | `ADVANCED_RECOMMENDATIONS_AR.md` |
| `QUICKSTART_FACE_TRAINING.md` | مكرر | `README_AR.md` |
| `QUICKSTART_WEB_APP_AR.md` | مكرر | `README_AR.md` |
| `README_FACE_TRAINING_AR.md` | مكرر | `README_AR.md` |
| `SIMPLE_EXPLANATION_AR.md` | مكرر | `MODELS_SUMMARY_AR.md` |
| `WEB_APP_IMPROVEMENTS_AR.md` | مكرر | `ENHANCEMENTS_SUMMARY_AR.md` |

---

## 🗺️ خريطة الاستخدام

### للمستخدم العادي:
```
1. README_AR.md          → دليل البدء
2. run_web_app.py        → تشغيل النظام
3. add_employee.py       → إضافة موظفين
4. generate_report.py    → التقارير
```

### للمطور:
```
1. README_AR.md                    → نظرة عامة
2. ACCURACY_IMPROVEMENTS_AR.md     → التحسينات الجديدة
3. src/advanced_activity_detector.py → الكود المحسّن
4. test_enhanced_system.py         → اختبار
```

### للمسؤول:
```
1. ADMIN_GUIDE_AR.md              → دليل الإدارة
2. PROJECT_STATUS_AR.md           → حالة النظام
3. ADD_CAMERA_GUIDE_AR.md         → إضافة كاميرات
4. web_app/                       → لوحة التحكم
```

---

## 📊 إحصائيات المشروع

### الملفات النشطة:
- **Python Scripts:** 8 ملفات
- **Source Code (src/):** 39 ملف
- **Web App:** 17 ملف
- **Documentation:** 8 ملفات رئيسية
- **Config:** 4 ملفات

### الملفات المؤرشفة:
- **Old Scripts:** 11 ملف
- **Old Docs:** 9 ملفات
- **Total Archived:** 20 ملف

### التحسين:
- **قبل:** 67 ملف في الجذر
- **بعد:** 20 ملف نشط + 20 مؤرشف
- **التنظيم:** تحسن بنسبة 70%

---

## 🔍 كيفية البحث

### للبحث عن موضوع معين:

#### **كشف الأنشطة:**
- `ACCURACY_IMPROVEMENTS_AR.md` - التحسينات
- `src/advanced_activity_detector.py` - الكود
- `MODELS_SUMMARY_AR.md` - شرح النماذج

#### **التعرف على الوجوه:**
- `src/enhanced_face_recognition.py` - الكود المحسّن
- `train_faces.py` - التدريب
- `MODELS_SUMMARY_AR.md` - التفاصيل

#### **تطبيق الويب:**
- `run_web_app.py` - التشغيل
- `web_app/app.py` - الكود الرئيسي
- `web_app/templates/` - الواجهات

#### **الإعدادات:**
- `config.json` - إعدادات عامة
- `config/` - إعدادات متقدمة

---

## ⚡ أوامر سريعة

```bash
# تشغيل النظام
python run_web_app.py

# اختبار التحسينات
python test_enhanced_system.py

# إضافة موظف
python add_employee.py

# تدريب الوجوه
python train_faces.py

# إنشاء تقرير
python generate_report.py

# اختبارات الوحدات
python run_tests.py

# الكاميرات المتعددة
python run_multi_camera.py
```

---

## 🎯 التوصيات

### للمبتدئين:
1. ابدأ بـ `README_AR.md`
2. شغّل `run_web_app.py`
3. اقرأ `START_HERE_AR.md`

### للمتقدمين:
1. راجع `ACCURACY_IMPROVEMENTS_AR.md`
2. جرّب `test_enhanced_system.py`
3. اقرأ `ADVANCED_RECOMMENDATIONS_AR.md`

### للمطورين:
1. افحص `src/advanced_activity_detector.py`
2. افحص `src/enhanced_face_recognition.py`
3. راجع التوثيق في `docs/`

---

## 📝 ملاحظات مهمة

✅ **جميع الملفات المؤرشفة محفوظة** في `archive_old_files/`
✅ **يمكن الرجوع إليها** في أي وقت
✅ **النظام الحالي** يعمل بكفاءة عالية بدون الملفات القديمة
✅ **الدقة محسّنة** إلى 85%+ مع الملفات الجديدة

---

## 🔄 آخر تحديث
**التاريخ:** 11 نوفمبر 2025
**الإصدار:** 2.0 (Enhanced System)
**الدقة:** 85-88%
