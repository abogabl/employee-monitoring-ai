# 💻 نظام التعلم الذاتي: الكود والتنفيذ
## Self-Learning System: Implementation

**تاريخ:** 17 نوفمبر 2025

---

## 📋 المحتويات

1. هيكل الملفات
2. الكود الأساسي
3. قاعدة البيانات
4. واجهة التأكيد
5. التكامل مع النظام الحالي

**اقرأ أولاً:** `SELF_LEARNING_PLAN_OVERVIEW_AR.md`

---

## 📁 هيكل الملفات المقترح

```
employee-monitoring-ai/
├── src/
│   └── self_learning/
│       ├── __init__.py
│       ├── data_collector.py         # مُجمِّع البيانات
│       ├── quality_assessor.py       # مُقيِّم الجودة
│       ├── active_learner.py         # التعلم النشط
│       ├── continuous_trainer.py     # المُدرِّب المستمر
│       ├── database.py               # قاعدة البيانات
│       └── models.py                 # نماذج البيانات
│
├── web_app/
│   ├── templates/
│   │   └── confirmation/
│   │       ├── queue.html            # قائمة التأكيد
│   │       └── confirm_identity.html # تأكيد الهوية
│   └── routes/
│       └── confirmation.py           # مسارات التأكيد
│
├── training_data/
│   └── auto_collected/               # البيانات المجمعة تلقائياً
│       ├── EMP001/
│       ├── EMP002/
│       └── ...
│
└── config/
    └── self_learning_config.json     # إعدادات التعلم الذاتي
```

---

## 💾 قاعدة البيانات

### الجداول المطلوبة

```sql
-- جدول الصور التدريبية
CREATE TABLE IF NOT EXISTS training_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id VARCHAR(50) NOT NULL,
    image_path TEXT NOT NULL,
    capture_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    confidence FLOAT,
    quality_score FLOAT,
    quality_details TEXT,  -- JSON
    metadata TEXT,         -- JSON
    validated BOOLEAN DEFAULT 0,
    used_in_training BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
);

-- جدول التصحيحات البشرية
CREATE TABLE IF NOT EXISTS human_corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id INTEGER NOT NULL,
    original_prediction VARCHAR(50),
    corrected_to VARCHAR(50),
    confidence FLOAT,
    corrected_by VARCHAR(50),
    correction_reason TEXT,
    corrected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (image_id) REFERENCES training_images(id),
    FOREIGN KEY (corrected_to) REFERENCES employees(employee_id)
);

-- جدول حالات التأكيد
CREATE TABLE IF NOT EXISTS confirmation_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, confirmed, rejected
    priority INTEGER DEFAULT 5,
    top_predictions TEXT,  -- JSON array
    assigned_to VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    processed_at DATETIME,
    FOREIGN KEY (image_id) REFERENCES training_images(id)
);

-- جدول أداء النماذج
CREATE TABLE IF NOT EXISTS model_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_version VARCHAR(20) NOT NULL,
    accuracy FLOAT,
    precision_score FLOAT,
    recall_score FLOAT,
    f1_score FLOAT,
    training_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    num_employees INTEGER,
    num_training_images INTEGER,
    training_duration_seconds INTEGER,
    notes TEXT
);

-- فهارس للأداء
CREATE INDEX idx_training_images_employee ON training_images(employee_id);
CREATE INDEX idx_training_images_timestamp ON training_images(capture_timestamp);
CREATE INDEX idx_confirmation_status ON confirmation_queue(status);
CREATE INDEX idx_model_performance_date ON model_performance(training_date);
```

---

## 🔧 الكود الأساسي

### 1. مُجمِّع البيانات (Data Collector)

```python
# src/self_learning/data_collector.py

import cv2
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
import numpy as np

logger = logging.getLogger(__name__)

class AutoDataCollector:
    """جمع بيانات تدريب تلقائياً من الكاميرات"""
    
    def __init__(self, storage_path: str = "training_data/auto_collected"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # معايير القبول
        self.min_confidence = 0.85
        self.min_quality_score = 0.70
        self.max_daily_images = 20
        
    def should_collect(self, employee_id: str, confidence: float, 
                      quality_score: float) -> bool:
        """تحديد ما إذا كان يجب جمع هذه الصورة"""
        
        # فحص الثقة والجودة
        if confidence < self.min_confidence or quality_score < self.min_quality_score:
            return False
            
        # فحص الحصة اليومية
        today_count = self._count_today_images(employee_id)
        if today_count >= self.max_daily_images:
            return False
            
        return True
    
    def collect_sample(self, face_image: np.ndarray, employee_id: str,
                      confidence: float, quality_score: float,
                      quality_details: dict, metadata: dict) -> Optional[str]:
        """جمع وحفظ عينة تدريب"""
        
        if not self.should_collect(employee_id, confidence, quality_score):
            return None
        
        # إنشاء مسار الحفظ
        emp_dir = self.storage_path / employee_id
        emp_dir.mkdir(exist_ok=True)
        
        # اسم الملف
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{timestamp}_c{confidence:.2f}_q{quality_score:.2f}.jpg"
        filepath = emp_dir / filename
        
        # حفظ الصورة
        cv2.imwrite(str(filepath), face_image)
        
        # حفظ metadata
        meta_file = filepath.with_suffix('.json')
        full_metadata = {
            'employee_id': employee_id,
            'confidence': confidence,
            'quality_score': quality_score,
            'quality_details': quality_details,
            'timestamp': timestamp,
            'auto_collected': True,
            **metadata
        }
        
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(full_metadata, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✓ Collected: {employee_id}/{filename}")
        return str(filepath)
    
    def _count_today_images(self, employee_id: str) -> int:
        """عد الصور المجمعة اليوم"""
        emp_dir = self.storage_path / employee_id
        if not emp_dir.exists():
            return 0
        
        today = datetime.now().strftime("%Y%m%d")
        return len(list(emp_dir.glob(f"{today}_*.jpg")))
```

### 2. مُقيِّم الجودة (Quality Assessor)

```python
# src/self_learning/quality_assessor.py

import cv2
import numpy as np
from typing import Tuple, Dict

class QualityAssessor:
    """تقييم جودة صور الوجوه"""
    
    def __init__(self):
        self.weights = {
            'sharpness': 0.30,
            'brightness': 0.25,
            'face_size': 0.25,
            'contrast': 0.20
        }
    
    def assess(self, face_image: np.ndarray) -> Tuple[float, Dict]:
        """تقييم جودة الصورة"""
        scores = {}
        
        # 1. الوضوح
        scores['sharpness'] = self._assess_sharpness(face_image)
        
        # 2. الإضاءة
        scores['brightness'] = self._assess_brightness(face_image)
        
        # 3. حجم الوجه
        scores['face_size'] = self._assess_size(face_image)
        
        # 4. التباين
        scores['contrast'] = self._assess_contrast(face_image)
        
        # الدرجة الإجمالية
        total = sum(scores[k] * self.weights[k] for k in scores)
        
        return total, scores
    
    def _assess_sharpness(self, image: np.ndarray) -> float:
        """قياس الوضوح"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        return min(lap_var / 100.0, 1.0)
    
    def _assess_brightness(self, image: np.ndarray) -> float:
        """قياس الإضاءة"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        mean_brightness = gray.mean()
        
        # أفضل: 80-180
        if 80 <= mean_brightness <= 180:
            return 1.0
        elif mean_brightness < 80:
            return mean_brightness / 80.0
        else:
            return max(0, 1.0 - (mean_brightness - 180) / 75.0)
    
    def _assess_size(self, image: np.ndarray) -> float:
        """تقييم حجم الوجه"""
        h, w = image.shape[:2]
        area = h * w
        # حجم مثالي: 200x200 = 40000
        return min(area / 40000.0, 1.0)
    
    def _assess_contrast(self, image: np.ndarray) -> float:
        """قياس التباين"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        std = gray.std()
        # تباين جيد: std > 40
        return min(std / 40.0, 1.0)
```

### 3. التعلم النشط (Active Learner)

```python
# src/self_learning/active_learner.py

from typing import List, Dict

class ActiveLearner:
    """اختيار أفضل العينات للتعلم"""
    
    def __init__(self, uncertainty_threshold: float = 0.75):
        self.uncertainty_threshold = uncertainty_threshold
    
    def identify_uncertain_cases(self, predictions: List[Dict]) -> List[Dict]:
        """تحديد الحالات التي تحتاج تأكيد"""
        uncertain = []
        
        for pred in predictions:
            confidence = pred['confidence']
            
            # ثقة منخفضة
            if 0.60 < confidence < self.uncertainty_threshold:
                pred['reason'] = 'low_confidence'
                pred['priority'] = 8
                uncertain.append(pred)
            
            # توقعات متقاربة
            elif self._has_close_predictions(pred):
                pred['reason'] = 'ambiguous'
                pred['priority'] = 9
                uncertain.append(pred)
            
            # وجه غير معروف
            elif confidence < 0.60:
                pred['reason'] = 'unknown_face'
                pred['priority'] = 10
                uncertain.append(pred)
        
        # ترتيب حسب الأولوية
        return sorted(uncertain, key=lambda x: x['priority'], reverse=True)
    
    def _has_close_predictions(self, pred: Dict, margin: float = 0.15) -> bool:
        """فحص التوقعات المتقاربة"""
        if 'top_predictions' not in pred or len(pred['top_predictions']) < 2:
            return False
        
        top1 = pred['top_predictions'][0]['confidence']
        top2 = pred['top_predictions'][1]['confidence']
        
        return (top1 - top2) < margin
```

### 4. المُدرِّب المستمر (Continuous Trainer)

```python
# src/self_learning/continuous_trainer.py

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class ContinuousTrainer:
    """تدريب مستمر للنماذج"""
    
    def __init__(self, min_samples: int = 50):
        self.min_samples = min_samples
        self.last_training = None
        self.training_interval_days = 7
    
    def should_update(self) -> bool:
        """هل يجب التحديث؟"""
        
        # فحص عدد الصور الجديدة
        if not self._has_enough_samples():
            logger.info("لا توجد صور كافية للتدريب")
            return False
        
        # فحص الوقت منذ آخر تدريب
        if self.last_training:
            days_since = (datetime.now() - self.last_training).days
            if days_since < self.training_interval_days:
                logger.info(f"آخر تدريب كان منذ {days_since} يوم فقط")
                return False
        
        return True
    
    def _has_enough_samples(self) -> int:
        """فحص عدد الصور الجديدة"""
        # TODO: فحص قاعدة البيانات
        return self.min_samples
    
    def fine_tune(self, model, new_data):
        """Fine-tuning خفيف"""
        logger.info("🔄 بدء Fine-tuning...")
        
        # تجميد الطبقات الأولى
        for layer in model.layers[:-3]:
            layer.trainable = False
        
        # تدريب الطبقات الأخيرة
        history = model.fit(
            new_data,
            epochs=5,
            batch_size=32,
            validation_split=0.2
        )
        
        self.last_training = datetime.now()
        logger.info("✓ Fine-tuning مكتمل")
        
        return history
    
    def full_retrain(self, model, all_data):
        """إعادة تدريب كاملة"""
        logger.info("🔄 بدء Full Retraining...")
        
        # تدريب كامل
        history = model.fit(
            all_data,
            epochs=20,
            batch_size=64,
            validation_split=0.2
        )
        
        self.last_training = datetime.now()
        logger.info("✓ Retraining مكتمل")
        
        return history
```

---

## 🌐 واجهة التأكيد

### 1. قالب قائمة التأكيد

```html
<!-- web_app/templates/confirmation/queue.html -->

{% extends "base.html" %}

{% block content %}
<div class="container mt-4">
    <h2><i class="bi bi-question-circle"></i> قائمة التأكيد</h2>
    
    <div class="row mt-4">
        <div class="col-md-12">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>الأولوية</th>
                        <th>الصورة</th>
                        <th>التوقعات</th>
                        <th>السبب</th>
                        <th>الوقت</th>
                        <th>إجراء</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in queue_items %}
                    <tr>
                        <td>
                            <span class="badge bg-{{ 'danger' if item.priority > 8 else 'warning' }}">
                                {{ item.priority }}
                            </span>
                        </td>
                        <td>
                            <img src="{{ item.image_url }}" class="img-thumbnail" style="max-width: 80px;">
                        </td>
                        <td>
                            {% for pred in item.top_predictions[:2] %}
                            <div>{{ pred.name }}: {{ "%.0f"|format(pred.confidence * 100) }}%</div>
                            {% endfor %}
                        </td>
                        <td>{{ item.reason_ar }}</td>
                        <td>{{ item.created_at|format_datetime }}</td>
                        <td>
                            <a href="{{ url_for('confirmation.confirm', id=item.id) }}" 
                               class="btn btn-sm btn-primary">
                                <i class="bi bi-check-circle"></i> تأكيد
                            </a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}
```

### 2. قالب تأكيد الهوية

```html
<!-- web_app/templates/confirmation/confirm_identity.html -->

{% extends "base.html" %}

{% block content %}
<div class="container mt-4">
    <h2><i class="bi bi-person-check"></i> تأكيد الهوية</h2>
    
    <div class="row mt-4">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header bg-warning">
                    <h5><i class="bi bi-camera"></i> الصورة المُلتقطة</h5>
                </div>
                <div class="card-body text-center">
                    <img src="{{ item.image_url }}" class="img-fluid" style="max-height: 400px;">
                </div>
            </div>
        </div>
        
        <div class="col-md-6">
            <div class="card">
                <div class="card-header bg-info text-white">
                    <h5><i class="bi bi-list-check"></i> من هذا الشخص؟</h5>
                </div>
                <div class="card-body">
                    <form method="POST">
                        <!-- التوقعات الأعلى -->
                        <h6>الاحتمالات:</h6>
                        {% for pred in item.top_predictions %}
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="radio" 
                                   name="employee_id" value="{{ pred.employee_id }}"
                                   id="pred{{ loop.index }}">
                            <label class="form-check-label" for="pred{{ loop.index }}">
                                <strong>{{ pred.name }}</strong> 
                                ({{ "%.0f"|format(pred.confidence * 100) }}%)
                            </label>
                        </div>
                        {% endfor %}
                        
                        <hr>
                        
                        <!-- اختيار من القائمة -->
                        <h6>أو اختر من القائمة:</h6>
                        <select name="employee_id" class="form-select mb-3">
                            <option value="">-- اختر موظف --</option>
                            {% for emp in all_employees %}
                            <option value="{{ emp.employee_id }}">{{ emp.name }}</option>
                            {% endfor %}
                        </select>
                        
                        <hr>
                        
                        <!-- خيارات أخرى -->
                        <div class="form-check mb-2">
                            <input class="form-check-input" type="radio" 
                                   name="action" value="unknown" id="unknown">
                            <label class="form-check-label" for="unknown">
                                شخص غير مسجل / زائر
                            </label>
                        </div>
                        
                        <div class="form-check mb-3">
                            <input class="form-check-input" type="radio" 
                                   name="action" value="skip" id="skip">
                            <label class="form-check-label" for="skip">
                                تجاهل / غير واضح
                            </label>
                        </div>
                        
                        <!-- أزرار -->
                        <div class="d-grid gap-2">
                            <button type="submit" class="btn btn-success btn-lg">
                                <i class="bi bi-check-circle"></i> تأكيد
                            </button>
                            <a href="{{ url_for('confirmation.queue') }}" 
                               class="btn btn-secondary">
                                <i class="bi bi-arrow-left"></i> رجوع
                            </a>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### 3. مسارات التأكيد

```python
# web_app/routes/confirmation.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
from src.self_learning.database import SelfLearningDB

confirmation_bp = Blueprint('confirmation', __name__, url_prefix='/confirmation')
db = SelfLearningDB()

@confirmation_bp.route('/queue')
def queue():
    """عرض قائمة التأكيد"""
    queue_items = db.get_pending_confirmations()
    return render_template('confirmation/queue.html', queue_items=queue_items)

@confirmation_bp.route('/confirm/<int:id>', methods=['GET', 'POST'])
def confirm(id):
    """تأكيد هوية"""
    item = db.get_confirmation_item(id)
    
    if request.method == 'POST':
        employee_id = request.form.get('employee_id')
        action = request.form.get('action')
        
        if action == 'unknown':
            db.mark_as_unknown(id)
            flash('تم تسجيل كشخص غير مسجل', 'info')
        elif action == 'skip':
            db.skip_confirmation(id)
            flash('تم التجاهل', 'warning')
        elif employee_id:
            db.confirm_identity(id, employee_id)
            flash(f'تم التأكيد بنجاح', 'success')
        else:
            flash('يُرجى الاختيار', 'danger')
            return redirect(url_for('confirmation.confirm', id=id))
        
        return redirect(url_for('confirmation.queue'))
    
    all_employees = db.get_all_employees()
    return render_template('confirmation/confirm_identity.html', 
                          item=item, all_employees=all_employees)
```

---

## 🔗 التكامل مع النظام الحالي

### التعديلات على معالج الفيديو

```python
# في src/simple_video_processor.py أو level2_video_processor.py

from src.self_learning.data_collector import AutoDataCollector
from src.self_learning.quality_assessor import QualityAssessor
from src.self_learning.active_learner import ActiveLearner

class VideoProcessor:
    def __init__(self):
        # ... كود موجود ...
        
        # إضافة مكونات التعلم الذاتي
        self.data_collector = AutoDataCollector()
        self.quality_assessor = QualityAssessor()
        self.active_learner = ActiveLearner()
    
    def process_frame(self, frame):
        # ... معالجة عادية ...
        
        # بعد التعرف على الوجه
        if face_detected:
            employee_id = recognition_result['employee_id']
            confidence = recognition_result['confidence']
            
            # تقييم جودة الصورة
            quality_score, quality_details = self.quality_assessor.assess(face_image)
            
            # جمع للتدريب إذا كانت الجودة عالية
            if confidence > 0.85 and quality_score > 0.70:
                self.data_collector.collect_sample(
                    face_image, employee_id,
                    confidence, quality_score,
                    quality_details, metadata
                )
            
            # إضافة للتأكيد إذا كانت غير مؤكدة
            elif 0.60 < confidence < 0.85:
                uncertain_cases = self.active_learner.identify_uncertain_cases([{
                    'employee_id': employee_id,
                    'confidence': confidence,
                    'face_image': face_image,
                    'top_predictions': recognition_result.get('top_predictions', [])
                }])
                
                if uncertain_cases:
                    # إضافة لقائمة التأكيد
                    db.add_to_confirmation_queue(uncertain_cases[0])
```

---

## ✨ الخلاصة

### الملفات التي يجب إنشاؤها

- `src/self_learning/data_collector.py` ✓
- `src/self_learning/quality_assessor.py` ✓
- `src/self_learning/active_learner.py` ✓
- `src/self_learning/continuous_trainer.py` ✓
- `src/self_learning/database.py` (راجع قاعدة البيانات أعلاه)
- `web_app/templates/confirmation/queue.html` ✓
- `web_app/templates/confirmation/confirm_identity.html` ✓
- `web_app/routes/confirmation.py` ✓

### الخطوات التالية

1. **إنشاء الملفات** حسب الكود أعلاه
2. **إنشاء قاعدة البيانات** بتشغيل SQL
3. **اختبار المكونات** كل على حدة
4. **التكامل** مع النظام الحالي
5. **النشر والمراقبة** (راجع `SELF_LEARNING_DEPLOYMENT_AR.md`)

---

**المطور:** AI Assistant  
**الحالة:** جاهز للتنفيذ ✅
