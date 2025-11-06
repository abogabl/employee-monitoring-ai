# نظام مراقبة الموظفين بالذكاء الاصطناعي (Windows)

## المتطلبات
- Python 3.10 أو أحدث (موصى به 3.10)
- Windows 10/11

## التثبيت
1. إنشاء بيئة افتراضية:
   ```powershell
   py -3.10 -m venv .venv
   .venv\Scripts\activate
   ```
2. تثبيت الحزم:
   - التثبيت المباشر:
     ```powershell
     pip install -r requirements.txt
     ```
   - ملاحظة خاصة بـ PyTorch (نسخة CPU): للحصول على عجلات CPU فقط (أصغر حجماً)، يمكنك:
     ```powershell
     pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision
     ```

## التشغيل لأول مرة
1. إنشاء بنية المجلدات:
   ```powershell
   py setup.py
   ```
2. ضع صور وجوه الموظفين داخل: `employees_database/faces/`
3. ضع فيديوهات الاختبار داخل: `videos/`
4. عدّل الإعدادات في `config.json` حسب الحاجة.

## بنية المشروع
- src/
  - يحتوي كافة الأكواد المصدرية.
- employees_database/
  - faces/
- models/
- reports/
- attendance_db/
- videos/
- logs/
- config.json
- requirements.txt
- setup.py

## ملاحظات
- جميع المسارات مُدارة باستخدام `pathlib` ومتوافقة مع Windows.
- السجلات تحفظ داخل `logs/`، والتقارير داخل `reports/`.
