# 🚀 نظام التعلم الذاتي: النشر والمراقبة
## Self-Learning System: Deployment & Monitoring

**تاريخ:** 17 نوفمبر 2025

---

## 📋 المحتويات

1. خطة النشر
2. المراقبة والتقييم
3. الصيانة الدورية
4. حل المشاكل
5. أفضل الممارسات

**اقرأ قبل النشر:**
- `SELF_LEARNING_PLAN_OVERVIEW_AR.md`
- `SELF_LEARNING_IMPLEMENTATION_AR.md`

---

## 🚀 خطة النشر

### المرحلة 1: التحضير (يومان)

#### اليوم 1: الإعداد الأساسي

```bash
# 1. إنشاء المجلدات
mkdir -p training_data/auto_collected
mkdir -p logs/self_learning
mkdir -p backups/models

# 2. إنشاء قاعدة البيانات
python scripts/create_self_learning_db.py

# 3. إنشاء ملف الإعدادات
cp config/self_learning_config.example.json config/self_learning_config.json

# 4. تعديل الإعدادات حسب بيئتك
nano config/self_learning_config.json
```

**ملف الإعدادات:**
```json
{
  "data_collection": {
    "enabled": true,
    "min_confidence": 0.85,
    "min_quality": 0.70,
    "max_daily_images": 20,
    "storage_path": "training_data/auto_collected"
  },
  "training": {
    "schedule": "weekly",
    "min_samples": 50,
    "fine_tune_epochs": 5,
    "full_retrain_epochs": 20
  },
  "confirmation": {
    "uncertainty_threshold": 0.75,
    "auto_approve_threshold": 0.90
  },
  "monitoring": {
    "log_level": "INFO",
    "metrics_interval": 3600,
    "alert_email": "admin@company.com"
  }
}
```

#### اليوم 2: الاختبار الأولي

```bash
# 1. اختبار جمع البيانات
python -m pytest tests/test_data_collector.py -v

# 2. اختبار تقييم الجودة
python -m pytest tests/test_quality_assessor.py -v

# 3. اختبار قاعدة البيانات
python -m pytest tests/test_self_learning_db.py -v

# 4. اختبار واجهة التأكيد
python scripts/test_confirmation_ui.py
```

### المرحلة 2: النشر التدريجي (أسبوع)

#### الأسبوع 1: وضع المراقبة (Shadow Mode)

```python
# تفعيل الجمع فقط دون تدريب
{
  "data_collection": {"enabled": true},
  "training": {"enabled": false},
  "shadow_mode": true  # المراقبة فقط
}
```

**المهام:**
- ✅ مراقبة جودة البيانات المجمعة
- ✅ فحص حالات عدم التأكد
- ✅ قياس معدل الجمع اليومي
- ✅ التأكد من عدم وجود أخطاء

**المؤشرات المطلوبة:**
- معدل جمع: 500-1000 صورة/يوم
- معدل قبول: 70%+
- لا أخطاء في التخزين

#### الأسبوع 2: التدريب التجريبي

```bash
# تفعيل التدريب بحذر
python scripts/test_training.py --dry-run

# إذا نجح، تفعيل تدريب حقيقي
python scripts/run_weekly_training.py --backup-first
```

**قبل التدريب:**
- ✅ نسخ احتياطي للنموذج الحالي
- ✅ تجميع 500+ صورة جديدة
- ✅ فحص جودة البيانات
- ✅ إشعار الفريق

**بعد التدريب:**
- ✅ اختبار النموذج الجديد
- ✅ مقارنة الدقة
- ✅ نشر إذا تحسن أو ثبت

### المرحلة 3: التشغيل الكامل

```python
# تفعيل كامل النظام
{
  "data_collection": {"enabled": true},
  "training": {"enabled": true},
  "confirmation": {"enabled": true},
  "shadow_mode": false
}
```

---

## 📊 المراقبة والتقييم

### لوحة المراقبة الرئيسية

```python
# scripts/monitoring_dashboard.py

import streamlit as st
from src.self_learning.database import SelfLearningDB

db = SelfLearningDB()

st.title("🧠 لوحة مراقبة التعلم الذاتي")

# 1. إحصائيات الجمع اليومي
st.header("📸 جمع البيانات")
col1, col2, col3 = st.columns(3)

with col1:
    today_collected = db.get_today_collected_count()
    st.metric("الصور المجمعة اليوم", today_collected, 
              delta=f"+{today_collected - db.get_yesterday_count()}")

with col2:
    avg_quality = db.get_avg_quality_today()
    st.metric("متوسط الجودة", f"{avg_quality:.1%}")

with col3:
    pending_count = db.get_pending_confirmations_count()
    st.metric("تحتاج تأكيد", pending_count)

# 2. أداء النموذج
st.header("🎯 أداء النموذج")
latest_performance = db.get_latest_model_performance()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Accuracy", f"{latest_performance['accuracy']:.1%}")
col2.metric("Precision", f"{latest_performance['precision']:.1%}")
col3.metric("Recall", f"{latest_performance['recall']:.1%}")
col4.metric("F1 Score", f"{latest_performance['f1_score']:.1%}")

# 3. رسم بياني للتطور
st.header("📈 تطور الدقة")
history = db.get_performance_history(days=30)
st.line_chart(history, x='date', y='accuracy')

# 4. قائمة التأكيد
st.header("⚠️ حالات تحتاج تأكيد")
pending = db.get_pending_confirmations(limit=10)
st.dataframe(pending)
```

### المؤشرات الحيوية (Vital Metrics)

#### 1. جودة البيانات

```python
# مراقبة يومية
metrics = {
    'collected_today': db.count_today_images(),
    'avg_quality': db.avg_quality_score_today(),
    'acceptance_rate': db.acceptance_rate_today(),
    'diversity_score': db.diversity_score_today()
}

# تنبيهات
if metrics['collected_today'] < 100:
    alert("⚠️ عدد قليل من الصور المجمعة اليوم")
    
if metrics['avg_quality'] < 0.70:
    alert("⚠️ جودة البيانات منخفضة")
    
if metrics['diversity_score'] < 0.60:
    alert("⚠️ قلة التنوع في البيانات")
```

#### 2. أداء النموذج

```python
# مراقبة أسبوعية
def check_model_health():
    current = db.get_current_accuracy()
    last_week = db.get_last_week_accuracy()
    
    # انخفاض الدقة
    if current < last_week - 0.05:
        alert("🚨 انخفاض كبير في الدقة!")
        return False
    
    # دقة منخفضة جداً
    if current < 0.85:
        alert("🚨 دقة النموذج أقل من 85%")
        return False
    
    # false positives عالية
    fp_rate = db.get_false_positive_rate()
    if fp_rate > 0.10:
        alert("⚠️ معدل False Positives عالي")
    
    return True
```

#### 3. التدخل البشري

```python
# مراقبة يومية
def check_intervention_rate():
    pending = db.get_pending_count()
    total_today = db.get_total_detections_today()
    
    rate = pending / total_today if total_today > 0 else 0
    
    # معدل عالي = مشكلة
    if rate > 0.15:
        alert("⚠️ معدل التدخل البشري عالي (>15%)")
    
    # معدل قليل جداً = ممتاز
    if rate < 0.02:
        notify("✅ معدل تدخل ممتاز (<2%)")
    
    return rate
```

### التنبيهات التلقائية

```python
# config/alerts_config.json

{
  "alerts": [
    {
      "name": "low_accuracy",
      "condition": "accuracy < 0.85",
      "severity": "critical",
      "action": "email + sms",
      "message": "دقة النموذج انخفضت إلى {accuracy:.1%}"
    },
    {
      "name": "high_pending",
      "condition": "pending_count > 100",
      "severity": "warning",
      "action": "email",
      "message": "توجد {pending_count} حالة تحتاج تأكيد"
    },
    {
      "name": "training_failed",
      "condition": "training_status == 'failed'",
      "severity": "critical",
      "action": "email + sms + slack",
      "message": "فشل التدريب: {error_message}"
    }
  ]
}
```

---

## 🔧 الصيانة الدورية

### يومياً

```bash
# 1. فحص الصحة العامة
python scripts/daily_health_check.py

# 2. تنظيف الصور ذات الجودة المنخفضة
python scripts/cleanup_low_quality.py --days 7

# 3. نسخ احتياطي للبيانات الجديدة
python scripts/backup_daily_data.py
```

### أسبوعياً

```bash
# 1. التدريب المجدول
python scripts/weekly_training.py --auto

# 2. تقرير الأداء
python scripts/generate_weekly_report.py

# 3. فحص القرص والذاكرة
python scripts/check_resources.py

# 4. تحديث لوحة المراقبة
python scripts/update_dashboard.py
```

### شهرياً

```bash
# 1. Full retraining
python scripts/monthly_retraining.py --full

# 2. تنظيف شامل
python scripts/monthly_cleanup.py

# 3. مراجعة الإعدادات
python scripts/review_config.py

# 4. تقرير شامل للإدارة
python scripts/generate_monthly_report.py
```

### سياسة الاحتفاظ بالبيانات

```python
# config/retention_policy.json

{
  "retention": {
    "high_quality_images": "permanent",
    "medium_quality_images": "6_months",
    "low_quality_images": "1_month",
    "rejected_images": "7_days",
    "training_logs": "1_year",
    "model_versions": "last_10"
  }
}
```

---

## 🔍 حل المشاكل

### المشكلة 1: لا يتم جمع بيانات

**الأعراض:**
- عدد الصور المجمعة = 0
- لا حالات تأكيد

**التشخيص:**
```bash
# فحص الإعدادات
python scripts/diagnose.py --check-collection

# فحص السجلات
tail -f logs/self_learning/data_collector.log
```

**الحلول المحتملة:**
1. التأكد من تفعيل `data_collection.enabled = true`
2. خفض `min_confidence` مؤقتاً إلى 0.80
3. خفض `min_quality` إلى 0.65
4. فحص صلاحيات المجلدات

### المشكلة 2: جودة البيانات منخفضة

**الأعراض:**
- `avg_quality < 0.60`
- معظم الصور مرفوضة

**التشخيص:**
```python
# تحليل أسباب الرفض
python scripts/analyze_rejections.py --last-days 7
```

**النتيجة:**
```
أسباب الرفض:
- إضاءة ضعيفة: 40%
- صورة مشوشة: 30%
- حجم صغير: 20%
- زاوية سيئة: 10%
```

**الحلول:**
1. تحسين إضاءة الكاميرات
2. ضبط Focus الكاميرا
3. زيادة دقة الكاميرا
4. خفض عتبة الجودة مؤقتاً

### المشكلة 3: دقة النموذج انخفضت

**الأعراض:**
- `accuracy < 0.85`
- زيادة في الأخطاء

**التشخيص:**
```bash
# تحليل الأخطاء
python scripts/analyze_errors.py

# مقارنة بالنموذج السابق
python scripts/compare_models.py --current --previous
```

**الحلول:**
1. **Rollback للنموذج السابق:**
```bash
python scripts/rollback_model.py --to-version v1.2.3
```

2. **إعادة تدريب بضبط أفضل:**
```bash
python scripts/retrain.py --tune-hyperparameters
```

3. **تنظيف البيانات السيئة:**
```bash
python scripts/clean_bad_data.py --threshold 0.60
```

### المشكلة 4: حالات تأكيد كثيرة

**الأعراض:**
- `pending_count > 100`
- معدل تأكيد > 15%

**الأسباب المحتملة:**
1. النموذج غير واثق (يحتاج تدريب)
2. موظفون جدد لم يُدرَّبوا
3. عتبة الثقة عالية جداً

**الحلول:**
```python
# 1. خفض عتبة عدم التأكد
{
  "confirmation": {
    "uncertainty_threshold": 0.70  # كانت 0.75
  }
}

# 2. تدريب سريع
python scripts/emergency_training.py

# 3. إضافة موظفين جدد بسرعة
python scripts/quick_add_employee.py --batch
```

---

## 💡 أفضل الممارسات

### 1. النسخ الاحتياطي

```bash
# نسخ احتياطي تلقائي قبل كل تدريب
def backup_before_training():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # نسخ النموذج
    shutil.copy(
        "models/face_encodings.pkl",
        f"backups/models/face_encodings_{timestamp}.pkl"
    )
    
    # نسخ قاعدة البيانات
    shutil.copy(
        "attendance_db/database.db",
        f"backups/db/database_{timestamp}.db"
    )
    
    logger.info(f"✓ Backup created: {timestamp}")
```

### 2. اختبار A/B للنماذج الجديدة

```python
# لا تستبدل النموذج مباشرة
def ab_test_new_model(new_model, old_model, test_data):
    # اختبار على 20% من البيانات
    sample = test_data.sample(frac=0.2)
    
    new_acc = evaluate(new_model, sample)
    old_acc = evaluate(old_model, sample)
    
    if new_acc > old_acc + 0.01:  # تحسن 1%+
        logger.info(f"✓ نموذج جديد أفضل: {new_acc:.2%} vs {old_acc:.2%}")
        return True
    else:
        logger.warning(f"✗ نموذج جديد ليس أفضل بما يكفي")
        return False
```

### 3. المراقبة المستمرة

```python
# تشغيل مراقبة في الخلفية
import threading

def continuous_monitoring():
    while True:
        try:
            # فحص كل ساعة
            check_model_health()
            check_data_quality()
            check_storage_space()
            
            time.sleep(3600)  # ساعة
            
        except Exception as e:
            logger.error(f"خطأ في المراقبة: {e}")
            alert_admin(f"Monitoring error: {e}")

# بدء المراقبة
monitor_thread = threading.Thread(target=continuous_monitoring, daemon=True)
monitor_thread.start()
```

### 4. التوثيق الكامل

```python
# سجل كل تغيير مهم
def log_important_event(event_type, details):
    db.insert_event_log({
        'timestamp': datetime.now(),
        'event_type': event_type,
        'details': json.dumps(details),
        'user': current_user,
        'system_state': get_system_state()
    })
```

---

## 📈 مؤشرات النجاح

### بعد شهر

- ✅ جمع تلقائي يعمل: 500+ صورة/يوم
- ✅ جودة البيانات: 70%+ مقبولة
- ✅ تدريب أسبوعي ناجح
- ✅ دقة مستقرة أو متحسنة

### بعد 3 أشهر

- ✅ دقة محسنة: 90% → 93%+
- ✅ تدخل بشري: < 5%
- ✅ تكيف تلقائي مع التغييرات
- ✅ نظام مستقل تماماً

### بعد 6 أشهر

- ✅ دقة عالية: 95%+
- ✅ تدخل بشري: < 2%
- ✅ 10,000+ صورة لكل موظف
- ✅ نموذج قوي ومستقر

---

## ✨ الخلاصة

### قائمة فحص النشر

**قبل النشر:**
- [ ] قاعدة البيانات جاهزة
- [ ] ملف الإعدادات مُعد
- [ ] الاختبارات كلها تعمل
- [ ] نسخ احتياطي للنظام الحالي
- [ ] لوحة المراقبة تعمل
- [ ] التنبيهات مُعدة

**بعد النشر:**
- [ ] مراقبة يومية لأول أسبوع
- [ ] تقرير أسبوعي للإدارة
- [ ] ضبط الإعدادات حسب الحاجة
- [ ] توثيق المشاكل والحلول

### الدعم

**للمشاكل:**
1. راجع السجلات: `logs/self_learning/`
2. شغل التشخيص: `python scripts/diagnose.py`
3. راجع هذا الملف: حل المشاكل

**للاستفسارات:**
- الوثائق: `SELF_LEARNING_*.md`
- الكود: `src/self_learning/`
- الأمثلة: `examples/self_learning/`

---

**المطور:** AI Assistant  
**الحالة:** جاهز للنشر ✅  
**آخر تحديث:** 17 نوفمبر 2025
