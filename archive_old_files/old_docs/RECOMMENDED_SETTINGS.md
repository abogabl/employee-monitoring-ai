# ⚙️ الإعدادات الموصى بها - Recommended Settings

## 🎯 إعدادات حسب نوع الجهاز

### 💻 **أجهزة مكتبية عادية**
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
    "activity_window": 15,
    "frame_skip": 3,
    "max_duration": 300
  },
  "performance": {
    "log_level": "INFO",
    "save_snapshots": true,
    "snapshot_quality": 95
  }
}
```

### 🖥️ **أجهزة قوية (i7, 16GB RAM+)**
```json
{
  "yolo": {
    "model": "yolov8m.pt",
    "imgsz": 640,
    "confidence": 0.3,
    "device": "cpu"
  },
  "level2_processor": {
    "enable_advanced_ai": true,
    "enable_face_recognition": true,
    "enable_activity_recognition": true,
    "activity_window": 20,
    "frame_skip": 2,
    "max_duration": 600
  },
  "ai_thresholds": {
    "anomaly_threshold": 0.6,
    "risk_threshold": 0.5,
    "prediction_confidence": 0.4
  }
}
```

### 📱 **أجهزة ضعيفة (i3, 4-8GB RAM)**
```json
{
  "yolo": {
    "model": "yolov8n.pt",
    "imgsz": 320,
    "confidence": 0.4,
    "device": "cpu"
  },
  "level2_processor": {
    "enable_advanced_ai": false,
    "enable_face_recognition": true,
    "enable_activity_recognition": true,
    "activity_window": 10,
    "frame_skip": 5,
    "max_duration": 120
  },
  "performance": {
    "log_level": "WARNING",
    "save_snapshots": true,
    "snapshot_quality": 85
  }
}
```

---

## 🎥 إعدادات حسب نوع الفيديو

### 📹 **فيديوهات قصيرة (1-5 دقائق)**
```json
{
  "level2_processor": {
    "frame_skip": 2,
    "max_duration": 300,
    "enable_advanced_ai": true
  },
  "ai_features": {
    "enable_anomaly_detection": true,
    "enable_behavior_prediction": true,
    "enable_risk_assessment": true
  }
}
```

### 🎬 **فيديوهات طويلة (5+ دقائق)**
```json
{
  "level2_processor": {
    "frame_skip": 4,
    "max_duration": 600,
    "enable_advanced_ai": true
  },
  "performance": {
    "enable_progress_tracking": true,
    "max_frame_analyses": 20
  }
}
```

### 📺 **كاميرات مباشرة**
```json
{
  "level2_processor": {
    "frame_skip": 3,
    "enable_advanced_ai": true,
    "activity_window": 30
  },
  "real_time": {
    "buffer_size": 10,
    "update_interval": 5
  }
}
```

---

## 🏢 إعدادات حسب بيئة العمل

### 🏭 **مصانع ومواقع إنتاج**
```json
{
  "ai_thresholds": {
    "anomaly_threshold": 0.8,
    "risk_threshold": 0.7,
    "prediction_confidence": 0.6
  },
  "safety_features": {
    "high_risk_alerts": true,
    "safety_equipment_detection": true,
    "restricted_area_monitoring": true
  },
  "activities": {
    "focus_on": ["working", "idle", "safety_violation"],
    "ignore": ["on_phone"]
  }
}
```

### 🏢 **مكاتب إدارية**
```json
{
  "ai_thresholds": {
    "anomaly_threshold": 0.6,
    "risk_threshold": 0.5,
    "prediction_confidence": 0.4
  },
  "office_features": {
    "productivity_tracking": true,
    "break_time_monitoring": true,
    "meeting_detection": true
  },
  "activities": {
    "focus_on": ["working", "on_phone", "idle"],
    "ignore": ["sleeping"]
  }
}
```

### 🛡️ **أمن ومراقبة**
```json
{
  "ai_thresholds": {
    "anomaly_threshold": 0.9,
    "risk_threshold": 0.8,
    "prediction_confidence": 0.7
  },
  "security_features": {
    "suspicious_behavior_detection": true,
    "unauthorized_access_alerts": true,
    "crowd_monitoring": true
  },
  "performance": {
    "high_accuracy_mode": true,
    "detailed_logging": true
  }
}
```

---

## 🕒 إعدادات حسب وقت العمل

### 🌅 **الوردية الصباحية (6 ص - 2 م)**
```json
{
  "time_settings": {
    "peak_hours": ["08:00", "12:00"],
    "break_times": ["10:00", "12:30"],
    "productivity_expectations": "high"
  },
  "ai_features": {
    "energy_level_tracking": true,
    "morning_productivity_analysis": true
  }
}
```

### 🌆 **الوردية المسائية (2 م - 10 م)**
```json
{
  "time_settings": {
    "peak_hours": ["14:00", "18:00"],
    "break_times": ["16:00", "19:00"],
    "productivity_expectations": "medium"
  },
  "ai_features": {
    "afternoon_fatigue_detection": true,
    "social_interaction_monitoring": true
  }
}
```

### 🌙 **الوردية الليلية (10 م - 6 ص)**
```json
{
  "time_settings": {
    "peak_hours": ["22:00", "02:00"],
    "break_times": ["00:00", "04:00"],
    "productivity_expectations": "low"
  },
  "ai_features": {
    "fatigue_detection": true,
    "alertness_monitoring": true,
    "safety_priority": true
  },
  "ai_thresholds": {
    "anomaly_threshold": 0.7,
    "risk_threshold": 0.6
  }
}
```

---

## 📊 إعدادات الأداء المتقدمة

### ⚡ **أداء سريع**
```json
{
  "performance_mode": "fast",
  "yolo": {
    "model": "yolov8n.pt",
    "imgsz": 320,
    "confidence": 0.4
  },
  "level2_processor": {
    "frame_skip": 5,
    "enable_advanced_ai": false,
    "activity_window": 10
  },
  "features": {
    "basic_detection": true,
    "face_recognition": true,
    "activity_recognition": true,
    "advanced_ai": false
  }
}
```

### 🎯 **دقة عالية**
```json
{
  "performance_mode": "accurate",
  "yolo": {
    "model": "yolov8l.pt",
    "imgsz": 640,
    "confidence": 0.25
  },
  "level2_processor": {
    "frame_skip": 1,
    "enable_advanced_ai": true,
    "activity_window": 30
  },
  "ai_thresholds": {
    "anomaly_threshold": 0.5,
    "risk_threshold": 0.4,
    "prediction_confidence": 0.3
  }
}
```

### ⚖️ **متوازن (موصى به)**
```json
{
  "performance_mode": "balanced",
  "yolo": {
    "model": "yolov8s.pt",
    "imgsz": 416,
    "confidence": 0.35
  },
  "level2_processor": {
    "frame_skip": 3,
    "enable_advanced_ai": true,
    "activity_window": 15
  },
  "ai_thresholds": {
    "anomaly_threshold": 0.7,
    "risk_threshold": 0.6,
    "prediction_confidence": 0.5
  }
}
```

---

## 🔧 إعدادات التخصيص

### 🎨 **واجهة المستخدم**
```json
{
  "ui_settings": {
    "language": "ar",
    "theme": "light",
    "show_confidence": true,
    "show_ai_insights": true,
    "auto_refresh": 30
  },
  "display": {
    "show_bounding_boxes": true,
    "show_activity_labels": true,
    "show_risk_indicators": true,
    "color_scheme": "professional"
  }
}
```

### 📈 **تقارير وإحصائيات**
```json
{
  "reporting": {
    "auto_generate": true,
    "frequency": "daily",
    "include_ai_insights": true,
    "include_recommendations": true,
    "export_formats": ["csv", "pdf", "json"]
  },
  "statistics": {
    "track_productivity": true,
    "track_attendance": true,
    "track_behavior_patterns": true,
    "historical_analysis": true
  }
}
```

---

## 🚨 إعدادات التنبيهات

### ⚠️ **تنبيهات أساسية**
```json
{
  "alerts": {
    "high_risk_behavior": true,
    "anomaly_detection": true,
    "productivity_drops": false,
    "unauthorized_access": true
  },
  "notification_methods": {
    "email": false,
    "web_popup": true,
    "log_file": true,
    "dashboard": true
  }
}
```

### 🔔 **تنبيهات متقدمة**
```json
{
  "advanced_alerts": {
    "behavior_prediction": true,
    "pattern_changes": true,
    "crowd_formation": true,
    "equipment_misuse": true
  },
  "alert_thresholds": {
    "risk_level": 0.7,
    "anomaly_score": 0.8,
    "confidence_drop": 0.3
  }
}
```

---

## 💾 إعدادات التخزين

### 📁 **تخزين أساسي**
```json
{
  "storage": {
    "save_processed_videos": true,
    "save_snapshots": true,
    "save_statistics": true,
    "retention_days": 30
  },
  "compression": {
    "video_quality": 85,
    "snapshot_quality": 95,
    "compress_old_files": true
  }
}
```

### 🗄️ **تخزين متقدم**
```json
{
  "advanced_storage": {
    "database_backup": true,
    "cloud_sync": false,
    "auto_cleanup": true,
    "archive_old_data": true
  },
  "data_management": {
    "max_storage_gb": 50,
    "cleanup_threshold": 80,
    "backup_frequency": "weekly"
  }
}
```

---

## 🎯 التوصيات النهائية

### **للبدء:**
1. استخدم الإعدادات **المتوازنة**
2. فعّل **جميع ميزات الذكاء الاصطناعي**
3. ابدأ بـ **frame_skip: 3**
4. استخدم **yolov8s.pt**

### **للتحسين:**
1. راقب الأداء لأسبوع
2. اضبط الإعدادات حسب النتائج
3. زد الدقة إذا كان الجهاز قوي
4. قلل الإعدادات إذا كان بطيء

### **للإنتاج:**
1. فعّل النسخ الاحتياطي
2. اضبط التنبيهات
3. راقب استخدام الموارد
4. حدّث الإعدادات دورياً

---

## ✅ قائمة التحقق

- [ ] اختر الإعدادات المناسبة لجهازك
- [ ] اضبط إعدادات بيئة العمل
- [ ] فعّل الميزات المطلوبة
- [ ] اختبر الأداء
- [ ] اضبط التنبيهات
- [ ] فعّل النسخ الاحتياطي

**الآن النظام مُعد بشكل مثالي! 🎉**
