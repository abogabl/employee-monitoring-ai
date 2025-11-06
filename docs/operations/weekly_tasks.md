# المهام الأسبوعية (Weekly Tasks)

## كل يوم أحد
- [ ] تحديث قائمة الموظفين (صفحة Employees أو تعديل employees_database/employees.json)
- [ ] مراجعة أداء النظام (Performance Monitor وتقارير FPS/CPU/MEM)
- [ ] فحص دقة التعرف على الوجوه (اختبر عينات جديدة، حسّن الصور)
- [ ] تحديث التقارير الأسبوعية وإرسالها للإدارة

## كل يوم أربعاء
- [ ] تحديث النماذج (YOLO/InsightFace) عند توفر نسخ أحدث بعد الاختبار
- [ ] صيانة قاعدة البيانات (VACUUM/REINDEX عبر daily_maintenance أو tools/validate_database.py)
- [ ] فحص الأمان (compliance_check.py و مراجعة security_config.json)
- [ ] نسخ احتياطي إضافي (BackupSystem.create_backup("full") وحفظ خارجي)

---

## ملاحظات تشغيلية
- أي تحديث نموذج يجب أن يسبق بمرحلة اختبار على بيئة staging ثم نقل للإنتاج.
- عند تعديل صلاحيات الموظفين/المشغلين، وثّق التغييرات في logs/audit.log.
