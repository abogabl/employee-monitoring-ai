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
from typing import Dict, Generator

from flask import Flask, Response, flash, redirect, render_template, request, session, url_for

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
    app.secret_key = "change-me"  # يجب استبداله في الإنتاج

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

    @app.route("/employees")
    @login_required
    def employees_page():
        return render_template("employees.html", employees=employees.list_all_employees())

    @app.post("/employees/add")
    @login_required(role="admin")
    def employees_add():
        emp_id = request.form.get("emp_id", "").strip()
        name = request.form.get("name", "").strip()
        if not emp_id or not name:
            flash("يرجى إدخال المعرف والاسم", "danger")
            return redirect(url_for("employees_page"))
        employees.add_employee(emp_id, name,
                               department=request.form.get("department", ""),
                               position=request.form.get("position", ""),
                               hire_date=request.form.get("hire_date", ""),
                               active=(request.form.get("active", "true").lower() == "true"))
        employees.save()
        flash("تم إضافة/تحديث الموظف", "success")
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
            data = json.loads(request.form.get("config_json", "{}"))
            Path("config").mkdir(parents=True, exist_ok=True)
            Path("config/cameras_config.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            flash("تم حفظ الإعدادات", "success")
        except Exception as e:
            flash(f"فشل حفظ الإعدادات: {e}", "danger")
        return redirect(url_for("settings_page"))

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
    app.run(host="127.0.0.1", port=5000, debug=True)
