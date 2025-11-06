# المهام اليومية (Daily Tasks)

## الصباح (8:00 صباحاً)
- [ ] فحص تشغيل كل الكاميرات (من Dashboard > Cameras أو عبر run_multi_camera.py)
- [ ] مراجعة التنبيهات الليلية (alert_monitor.py وتقارير logs/audit.log)
- [ ] التحقق من النسخ الاحتياطي الليلي (backups/ و daily_maintenance تقرير)
- [ ] فحص مساحة التخزين (Monitoring أو tools/system_info.py)

## أثناء اليوم
- [ ] مراقبة الـ Dashboard (الحضور، الكاميرات، التنبيهات)
- [ ] الرد على التنبيهات (email/telegram/webhook) ومعالجة الأسباب
- [ ] حل مشاكل الكاميرات (إعادة تشغيل الكاميرا/العملية من صفحة Cameras)
- [ ] معالجة طلبات الموظفين (تعديل بيانات/استخراج تقارير/تحديث صور)

## المساء (5:00 مساءً)
- [ ] إنشاء التقرير اليومي (Reports أو generate_report.py --type daily)
- [ ] مراجعة الحضور وإغلاق الجلسات المفتوحة إن لزم
- [ ] إرسال التقرير للإدارة (email notifier)
- [ ] فحص سلامة البيانات (tools/validate_database.py و compliance_check.py)

---

## أوامر مفيدة
- تشغيل لوحة الويب:
```bash
python run_web_app.py --host 0.0.0.0 --port 5000
```
- إنشاء تقرير يومي سريع:
```bash
python generate_report.py --type daily --date $(date +%F) --out reports/daily_$(date +%F).csv
```

## لقطات شاشة مقترحة (Screenshots)
- Dashboard الرئيسية (الحاضرون الآن، الكاميرات النشطة).
- صفحة Cameras (حالة الكاميرات وأزرار التحكم).
- صفحة Attendance (الجدول مع الفلاتر والتصدير).
