"""
تطبيق Flask لواجهة الإدارة.
- صفحات: Dashboard, Cameras, Employees, Attendance, Reports, Settings, Logs
- SSE للتحديثات الفورية
- تكامل بسيط مع الأنظمة القائمة
"""
from __future__ import annotations

import json
import logging
import queue
import threading
import time
from datetime import date
from pathlib import Path
from typing import Dict, Generator, List
import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Response, stream_template, send_from_directory
from werkzeug.utils import secure_filename

from src.attendance_system import AttendanceSystem
from src.employee_manager import EmployeeDatabase
from src.multi_camera_runner import MultiCameraRunner
from src.reporting import ReportGenerator
from .auth import auth_bp, login_required
from .api import api_bp

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("web_app")


def create_app(config_path: str = "config/cameras_config.json") -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    
    # إعدادات الأمان المحسّنة
    try:
        from config.security_config import (
            get_secret_key, 
            SESSION_COOKIE_SECURE,
            SESSION_COOKIE_HTTPONLY,
            SESSION_COOKIE_SAMESITE,
            PERMANENT_SESSION_LIFETIME
        )
        app.secret_key = get_secret_key()
        app.config['SESSION_COOKIE_SECURE'] = SESSION_COOKIE_SECURE
        app.config['SESSION_COOKIE_HTTPONLY'] = SESSION_COOKIE_HTTPONLY
        app.config['SESSION_COOKIE_SAMESITE'] = SESSION_COOKIE_SAMESITE
        app.config['PERMANENT_SESSION_LIFETIME'] = PERMANENT_SESSION_LIFETIME
        logger.info("✓ تم تحميل إعدادات الأمان المحسّنة")
    except ImportError:
        import secrets
        app.secret_key = secrets.token_hex(32)
        logger.warning("⚠️ استخدام مفتاح مؤقت - أنشئ config/security_config.py للإنتاج")

    # مكونات مشتركة
    runner = MultiCameraRunner(config_path)
    try:
        runner.load_config()
    except Exception:
        pass
    attendance = AttendanceSystem()
    employees = EmployeeDatabase()
    reports = ReportGenerator(attendance=attendance)

    # تسجيل Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp, url_prefix="/api/v1")

    # صفحات
    @app.route("/")
    @login_required
    def dashboard():
        today_rows = attendance.get_daily_attendance(date.today())
        present_now = [r for r in today_rows if r.get("check_out_time") is None]
        cams_status = runner.get_all_status() if runner.cameras else {}
        total_hours = 0.0
        ids = sorted({r["employee_id"] for r in today_rows})
        for eid in ids:
            total_hours += attendance.calculate_work_hours(eid, date.today())
        return render_template("dashboard.html",
                               present_count=len(set([r["employee_id"] for r in present_now])),
                               cameras_active=sum(1 for s in cams_status.values() if s.get("running")),
                               total_hours=round(total_hours, 2),
                               cams_status=cams_status,
                               )
    
    # Phase 11: صفحة تقرير الأنشطة اليومية
    @app.route("/activity-report")
    @login_required
    def activity_report():
        from datetime import datetime
        report_date = request.args.get('date', date.today().isoformat())
        
        # الحصول على بيانات الموظفين (بيانات تجريبية للعرض)
        emp_list = employees.list_employees()
        employees_data = []
        
        total_work = 0
        total_sleep = 0
        total_phone = 0
        
        for emp in emp_list:
            # جلب بيانات الأنشطة من قاعدة البيانات (حالياً بيانات تجريبية)
            work_hours = round(6 + (hash(emp.get('id', '')) % 30) / 10, 1)
            sleep_hours = round((hash(emp.get('id', '')) % 10) / 10, 1)
            phone_hours = round((hash(emp.get('id', '')) % 20) / 10, 1)
            productivity = max(0, min(100, int(100 * work_hours / (work_hours + sleep_hours + phone_hours + 0.1))))
            
            employees_data.append({
                'name': emp.get('name', 'Unknown'),
                'snapshot': emp.get('snapshot'),
                'work_hours': work_hours,
                'sleep_hours': sleep_hours,
                'phone_hours': phone_hours,
                'productivity': productivity
            })
            
            total_work += work_hours
            total_sleep += sleep_hours
            total_phone += phone_hours
        
        overall_productivity = int(100 * total_work / (total_work + total_sleep + total_phone + 0.1)) if employees_data else 0
        
        return render_template("activity_report.html",
                               today=report_date,
                               employees=employees_data,
                               total_work=round(total_work, 1),
                               total_sleep=round(total_sleep, 1),
                               total_phone=round(total_phone, 1),
                               productivity=overall_productivity)

    @app.route("/cameras")
    @login_required
    def cameras():
        cfg = runner.load_config()
        cams = cfg.get("cameras", [])
        status = runner.get_all_status()
        return render_template("cameras.html", cameras=cams, status=status)

    @app.post("/cameras/control")
    @login_required(role="operator")
    def cameras_control():
        action = request.form.get("action")
        cam_id = request.form.get("camera_id")
        if action == "start":
            cfg = next((c for c in runner.config.get("cameras", []) if c.get("id") == cam_id), None)
            if cfg:
                runner.start_camera(cfg)
        elif action == "stop":
            runner.stop_camera(cam_id)
        elif action == "restart":
            runner.restart_camera(cam_id)
        return redirect(url_for("cameras"))
    
    @app.post("/cameras/add")
    @login_required(role="admin")
    def camera_add():
        """إضافة كاميرا جديدة"""
        try:
            # قراءة التكوين الحالي
            config_path = Path("config/cameras_config.json")
            if config_path.exists():
                config = json.loads(config_path.read_text(encoding="utf-8"))
            else:
                config = {"cameras": []}
            
            # إنشاء كاميرا جديدة
            new_camera = {
                "id": request.form.get("camera_id", "").strip(),
                "name": request.form.get("name", "").strip(),
                "source": request.form.get("source", "").strip(),
                "enabled": request.form.get("enabled", "true") == "true",
                "device": request.form.get("device", "cpu"),
                "location": request.form.get("location", "").strip(),
                "priority": int(request.form.get("priority", 2)),
                "fps": int(request.form.get("fps", 25)),
                "imgsz": int(request.form.get("imgsz", 640)),
                "conf": float(request.form.get("conf", 0.5))
            }
            
            # تحويل المصدر إلى رقم إذا كان رقماً
            try:
                new_camera["source"] = int(new_camera["source"])
            except ValueError:
                pass  # إبقائه كنص (RTSP, HTTP, إلخ)
            
            # التحقق من عدم تكرار المعرف
            if any(c.get("id") == new_camera["id"] for c in config.get("cameras", [])):
                flash(f"الكاميرا بمعرف {new_camera['id']} موجودة بالفعل", "danger")
                return redirect(url_for("cameras"))
            
            # إضافة الكاميرا
            if "cameras" not in config:
                config["cameras"] = []
            config["cameras"].append(new_camera)
            
            # حفظ التكوين
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
            
            # إعادة تحميل التكوين
            runner.config = config
            
            flash(f"تم إضافة الكاميرا '{new_camera['name']}' بنجاح", "success")
        except Exception as e:
            flash(f"فشل إضافة الكاميرا: {e}", "danger")
        
        return redirect(url_for("cameras"))
    
    @app.post("/cameras/edit")
    @login_required(role="admin")
    def camera_edit():
        """تعديل كاميرا موجودة"""
        try:
            camera_id = request.form.get("camera_id", "").strip()
            
            # قراءة التكوين
            config_path = Path("config/cameras_config.json")
            if not config_path.exists():
                flash("ملف التكوين غير موجود", "danger")
                return redirect(url_for("cameras"))
            
            config = json.loads(config_path.read_text(encoding="utf-8"))
            
            # البحث عن الكاميرا
            camera = next((c for c in config.get("cameras", []) if c.get("id") == camera_id), None)
            if not camera:
                flash(f"الكاميرا {camera_id} غير موجودة", "danger")
                return redirect(url_for("cameras"))
            
            # تحديث البيانات
            camera["name"] = request.form.get("name", "").strip()
            camera["source"] = request.form.get("source", "").strip()
            camera["enabled"] = request.form.get("enabled", "true") == "true"
            camera["device"] = request.form.get("device", "cpu")
            camera["location"] = request.form.get("location", "").strip()
            camera["priority"] = int(request.form.get("priority", 2))
            camera["fps"] = int(request.form.get("fps", 25))
            camera["imgsz"] = int(request.form.get("imgsz", 640))
            camera["conf"] = float(request.form.get("conf", 0.5))
            
            # تحويل المصدر إلى رقم إذا كان رقماً
            try:
                camera["source"] = int(camera["source"])
            except ValueError:
                pass
            
            # حفظ التكوين
            config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
            
            # إعادة تحميل التكوين
            runner.config = config
            
            flash(f"تم تحديث الكاميرا '{camera['name']}' بنجاح", "success")
        except Exception as e:
            flash(f"فشل تحديث الكاميرا: {e}", "danger")
        
        return redirect(url_for("cameras"))
    
    @app.post("/cameras/delete")
    @login_required(role="admin")
    def camera_delete():
        """حذف كاميرا"""
        try:
            camera_id = request.form.get("camera_id", "").strip()
            
            # قراءة التكوين
            config_path = Path("config/cameras_config.json")
            if not config_path.exists():
                flash("ملف التكوين غير موجود", "danger")
                return redirect(url_for("cameras"))
            
            config = json.loads(config_path.read_text(encoding="utf-8"))
            
            # إيقاف الكاميرا أولاً إذا كانت تعمل
            try:
                runner.stop_camera(camera_id)
            except Exception as stop_err:
                logger.warning(f"تعذر إيقاف الكاميرا {camera_id}: {stop_err}")
            
            # حذف الكاميرا
            original_count = len(config.get("cameras", []))
            config["cameras"] = [c for c in config.get("cameras", []) if c.get("id") != camera_id]
            
            if len(config["cameras"]) == original_count:
                flash(f"الكاميرا {camera_id} غير موجودة", "warning")
            else:
                # حفظ التكوين
                config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
                
                # إعادة تحميل التكوين
                runner.config = config
                
                flash(f"تم حذف الكاميرا {camera_id} بنجاح", "success")
        except Exception as e:
            flash(f"فشل حذف الكاميرا: {e}", "danger")
        
        return redirect(url_for("cameras"))

    @app.route("/employees")
    @login_required
    def employees_page():
        search = request.args.get("search", "").strip()
        department = request.args.get("department", "").strip()
        all_emps = employees.list_all_employees()
        
        # فلترة
        filtered = all_emps
        if search:
            filtered = [e for e in filtered if search.lower() in e.get("name", "").lower() or search.lower() in e.get("emp_id", "").lower()]
        if department:
            filtered = [e for e in filtered if e.get("department", "") == department]
        
        # استخراج الأقسام للفلترة
        departments = sorted(set(e.get("department", "") for e in all_emps if e.get("department")))
        
        return render_template("employees.html", 
                             employees=filtered, 
                             all_employees=all_emps,
                             departments=departments,
                             search=search,
                             department=department)

    @app.post("/employees/add")
    @login_required(role="admin")
    def employees_add():
        emp_id = request.form.get("emp_id", "").strip()
        name = request.form.get("name", "").strip()
        if not emp_id or not name:
            flash("يرجى إدخال المعرف والاسم", "danger")
            return redirect(url_for("employees_page"))
        
        # معالجة الصورة
        photo_path = None
        if "photo" in request.files:
            photo = request.files["photo"]
            if photo and photo.filename:
                # التأكد من المجلد
                upload_folder = Path("web_app/static/uploads/employees")
                upload_folder.mkdir(parents=True, exist_ok=True)
                
                # حفظ الصورة
                filename = secure_filename(f"{emp_id}_{photo.filename}")
                photo_path_full = upload_folder / filename
                photo.save(photo_path_full)
                photo_path = f"uploads/employees/{filename}"
        
        employees.add_employee(emp_id, name,
                               department=request.form.get("department", ""),
                               position=request.form.get("position", ""),
                               hire_date=request.form.get("hire_date", ""),
                               active=(request.form.get("active", "true").lower() == "true"),
                               photo=photo_path)
        employees.save()
        flash("تم إضافة/تحديث الموظف بنجاح", "success")
        return redirect(url_for("employees_page"))
    
    @app.post("/employees/edit")
    @login_required(role="admin")
    def employees_edit():
        """تعديل موظف موجود"""
        emp_id = request.form.get("emp_id", "").strip()
        name = request.form.get("name", "").strip()
        if not emp_id or not name:
            flash("يرجى إدخال المعرف والاسم", "danger")
            return redirect(url_for("employees_page"))
        
        # معالجة الصورة
        photo_path = None
        if "photo" in request.files:
            photo = request.files["photo"]
            if photo and photo.filename:
                upload_folder = Path("web_app/static/uploads/employees")
                upload_folder.mkdir(parents=True, exist_ok=True)
                filename = secure_filename(f"{emp_id}_{photo.filename}")
                photo_path_full = upload_folder / filename
                photo.save(photo_path_full)
                photo_path = f"uploads/employees/{filename}"
        
        # إذا لم يتم رفع صورة جديدة، احتفظ بالصورة القديمة
        if not photo_path:
            emp = employees.get_employee(emp_id)
            if emp:
                photo_path = emp.get("photo")
        
        employees.add_employee(emp_id, name,
                               department=request.form.get("department", ""),
                               position=request.form.get("position", ""),
                               hire_date=request.form.get("hire_date", ""),
                               active=(request.form.get("active", "true").lower() == "true"),
                               photo=photo_path)
        employees.save()
        flash(f"تم تحديث بيانات الموظف '{name}' بنجاح", "success")
        return redirect(url_for("employees_page"))
    
    @app.post("/employees/delete")
    @login_required(role="admin")
    def employees_delete():
        """حذف موظف"""
        emp_id = request.form.get("emp_id", "").strip()
        if not emp_id:
            flash("معرف الموظف مطلوب", "danger")
            return redirect(url_for("employees_page"))
        
        # حذف الموظف
        if employees.delete_employee(emp_id):
            employees.save()
            flash(f"تم حذف الموظف {emp_id} بنجاح", "success")
        else:
            flash(f"الموظف {emp_id} غير موجود", "warning")
        
        return redirect(url_for("employees_page"))

    @app.route("/attendance")
    @login_required
    def attendance_page():
        d = request.args.get("date", date.today().isoformat())
        rows = attendance.get_daily_attendance(d)
        return render_template("attendance.html", rows=rows, date=d)

    @app.get("/attendance/export")
    @login_required(role="manager")
    def attendance_export():
        d = request.args.get("date", date.today().isoformat())
        df = attendance.generate_daily_report(d)
        out = Path("reports") / f"daily_{d}.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False, encoding="utf-8-sig")
        flash(f"تم حفظ التقرير في {out}", "success")
        return redirect(url_for("attendance_page", date=d))

    @app.route("/reports")
    @login_required
    def reports_page():
        return render_template("reports.html")

    @app.post("/reports/generate")
    @login_required(role="manager")
    def reports_generate():
        rtype = request.form.get("type", "daily")
        if rtype == "daily":
            d = request.form.get("date", date.today().isoformat())
            out = reports.generate_daily_summary(d, Path("reports") / f"daily_{d}.csv")
            flash(f"تم إنشاء تقرير يومي: {out}", "success")
        return redirect(url_for("reports_page"))

    @app.route("/settings")
    @login_required(role="admin")
    def settings_page():
        cfg = runner.config or {}
        cfg_json = json.dumps(cfg, ensure_ascii=False, indent=2)
        return render_template("settings.html", config=cfg, config_json=cfg_json)

    @app.post("/settings/update")
    @login_required(role="admin")
    def settings_update():
        try:
            new_data = json.loads(request.form.get("config_json", "{}"))
            
            # قراءة التكوين الحالي للحفاظ على الكاميرات
            config_path = Path("config/cameras_config.json")
            current_config = {}
            if config_path.exists():
                current_config = json.loads(config_path.read_text(encoding="utf-8"))
            
            # تحديث الإعدادات العامة فقط
            if 'global_settings' in new_data:
                current_config['global_settings'] = new_data['global_settings']
            
            # حفظ التكوين المدمج
            Path("config").mkdir(parents=True, exist_ok=True)
            config_path.write_text(json.dumps(current_config, ensure_ascii=False, indent=2), encoding="utf-8")
            
            # تحديث التكوين في الـ runner
            runner.config = current_config
            
            flash("تم حفظ الإعدادات بنجاح", "success")
        except Exception as e:
            flash(f"فشل حفظ الإعدادات: {e}", "danger")
        return redirect(url_for("settings_page"))

    @app.route("/employees/<emp_id>")
    @login_required
    def employee_detail(emp_id):
        """عرض تفاصيل موظف واحد"""
        emp = employees.get_employee(emp_id)
        if not emp:
            flash("الموظف غير موجود", "danger")
            return redirect(url_for("employees_page"))
        
        # جلب بيانات الحضور
        today_att = attendance.get_daily_attendance(date.today())
        emp_att = [r for r in today_att if r.get("employee_id") == emp_id]
        
        return render_template("employee_detail.html", employee=emp, attendance_today=emp_att)
    
    @app.route("/logs")
    @login_required
    def logs_page():
        log_file = Path("logs/app.log")
        lines = []
        if log_file.exists():
            try:
                lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()[-500:]
            except Exception:
                lines = []
        return render_template("logs.html", lines=lines)
    
    @app.route("/test-video")
    @login_required
    def test_video_page():
        """صفحة اختبار الفيديو"""
        return render_template("test_video.html")
    
    @app.route("/favicon.ico")
    def favicon():
        """أيقونة الموقع"""
        return send_from_directory(
            os.path.join(app.root_path, 'static'),
            'favicon.png',
            mimetype='image/png'
        )
    
    @app.post("/test-video/process")
    @login_required
    def test_video_process():
        """معالجة فيديو الاختبار مع AI حقيقي"""
        import time as time_module
        from src.level2_video_processor import Level2VideoProcessor
        from src.file_validator import FileValidator
        
        try:
            logger.info("=== بدء معالجة فيديو جديد ===")
            
            if 'video' not in request.files:
                logger.error("لم يتم العثور على ملف فيديو في الطلب")
                return jsonify({"success": False, "error": "لم يتم رفع ملف فيديو"})
            
            video_file = request.files['video']
            if video_file.filename == '':
                logger.error("اسم الملف فارغ")
                return jsonify({"success": False, "error": "لم يتم اختيار ملف"})
            
            # حفظ الفيديو المؤقت
            upload_folder = Path("web_app/static/uploads/test_videos")
            upload_folder.mkdir(parents=True, exist_ok=True)
            
            filename = secure_filename(video_file.filename)
            timestamp = int(time_module.time())
            input_path = upload_folder / f"input_{timestamp}_{filename}"
            output_filename = f"output_{timestamp}_{filename}"
            output_path = upload_folder / output_filename
            
            video_file.save(input_path)
            logger.info(f"تم حفظ الفيديو: {input_path}")
            
            # التحقق من صحة الفيديو
            logger.info("التحقق من صحة الفيديو...")
            validator = FileValidator(max_size_mb=500, max_duration_sec=600)
            is_valid, error_msg, video_info = validator.validate_video_file(input_path)
            
            if not is_valid:
                logger.error(f"الفيديو غير صحيح: {error_msg}")
                # حذف الملف غير الصحيح
                try:
                    input_path.unlink()
                except:
                    pass
                return jsonify({"success": False, "error": f"الملف غير صحيح: {error_msg}"})
            
            logger.info(f"✓ الفيديو صحيح: {video_info['duration_sec']:.1f}s, {video_info['resolution']}")
            
            # قراءة الإعدادات - Phase 10: محسنة للسرعة القصوى
            confidence = float(request.form.get('confidence', 0.45))
            frame_skip = int(request.form.get('frame_skip', 8))  # frame_skip=8 worked with ByteTrack
            max_duration = int(request.form.get('max_duration', 30))
            imgsz = int(request.form.get('imgsz', 480))  # Phase 10: 480p للسرعة
            # تفعيل التعرف على الوجوه والأنشطة للدقة الكاملة
            enable_face = True
            enable_activity = True
            
            # تهيئة معالج المستوى الثاني مع الذكاء الاصطناعي المتقدم
            # Phase 10: السرعة القصوى والدقة الكاملة
            logger.info("تهيئة Level2VideoProcessor مع الذكاء الاصطناعي المتقدم...")
            processor = Level2VideoProcessor(
                device="cpu",
                imgsz=480,            # Phase 10: 480p للسرعة القصوى
                conf_threshold=0.45,  # عتبة صارمة لتقليل المعرفات الوهمية
                enable_face_recognition=enable_face,
                enable_activity_recognition=enable_activity,
                enable_advanced_ai=True,
                yolo_model="s",
                activity_window=15
            )
            logger.info("تم تهيئة معالج المستوى الثاني بنجاح")
            
            # معالجة الفيديو مع progress tracking
            video_task_id = f"video_{timestamp}"
            logger.info(f"بدء معالجة الفيديو: {input_path} [Task ID: {video_task_id}]")
            logger.info(f"الإعدادات: imgsz={imgsz}, frame_skip={frame_skip}, confidence={confidence}")
            try:
                results = processor.process_video(
                    input_path=str(input_path),
                    output_path=str(output_path),
                    frame_skip=frame_skip,
                    max_duration=max_duration,
                    task_id=video_task_id,
                    enable_progress_tracking=True
                )
            except ValueError as e:
                logger.error(f"خطأ في صيغة الفيديو: {e}")
                return jsonify({
                    "success": False, 
                    "error": f"مشكلة في الفيديو: {str(e)}. تأكد من أن الفيديو صالح وغير تالف."
                })
            except Exception as e:
                logger.error(f"خطأ في معالجة الفيديو: {e}")
                return jsonify({
                    "success": False, 
                    "error": f"خطأ في المعالجة: {str(e)}"
                })
            logger.info("انتهت المعالجة")
            
            # إضافة task_id للنتائج (للعميل)
            results['task_id'] = video_task_id
            
            # حذف الملف الأصلي
            try:
                input_path.unlink()
                logger.info("تم حذف الملف المؤقت")
            except Exception as e:
                logger.warning(f"فشل حذف الملف المؤقت: {e}")
            
            # التحقق من الملف الناتج الفعلي (.mp4 أو .avi)
            actual_output = None
            if output_path.exists():
                actual_output = output_filename
            elif output_path.with_suffix('.avi').exists():
                actual_output = output_filename.replace('.mp4', '.avi')
            
            if actual_output:
                results['output_video'] = url_for('static', filename=f'uploads/test_videos/{actual_output}')
            else:
                logger.warning("الملف الناتج غير موجود!")
            
            logger.info(f"اكتملت المعالجة: {results.get('total_persons', 0)} أشخاص, {results.get('total_activities', 0)} نشاط")
            
            # إضافة success flag
            results['success'] = True
            return jsonify(results)
            
        except Exception as e:
            logger.exception("خطأ في معالجة الفيديو")
            return jsonify({"success": False, "error": str(e)}), 500

    # API للحصول على تقدم المعالجة
    @app.route("/api/progress/<task_id>")
    @login_required
    def get_progress(task_id: str):
        """الحصول على تقدم معالجة المهمة"""
        try:
            from src.progress_tracker import get_tracker
            tracker = get_tracker(task_id)
            if tracker:
                return jsonify(tracker.get_progress_dict())
            else:
                return jsonify({"error": "المهمة غير موجودة"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    # SSE للأحداث الفورية
    @app.route("/events")
    @login_required
    def sse_events() -> Response:
        def gen() -> Generator[str, None, None]:
            while True:
                try:
                    today_rows = attendance.get_daily_attendance(date.today())
                    present = len({r["employee_id"] for r in today_rows if r.get("check_out_time") is None})
                    cams_status = runner.get_all_status()
                    active_cams = sum(1 for s in cams_status.values() if s.get("running"))
                    payload = json.dumps({"present": present, "active_cams": active_cams})
                    yield f"data: {payload}\n\n"
                    time.sleep(2)
                except GeneratorExit:
                    break
                except Exception:
                    time.sleep(2)
        return Response(gen(), mimetype="text/event-stream")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5050, debug=True)
