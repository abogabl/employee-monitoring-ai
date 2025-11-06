"""
REST API v1 لتطبيق إدارة النظام.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Dict

from flask import Blueprint, jsonify, request

from src.attendance_system import AttendanceSystem
from src.employee_manager import EmployeeDatabase
from src.multi_camera_runner import MultiCameraRunner
from src.reporting import ReportGenerator

api_bp = Blueprint("api_v1", __name__)

# كائنات مشتركة مبسطة (يمكن لاحقاً حقنها من app factory)
_runner = MultiCameraRunner("config/cameras_config.json")
try:
    _runner.load_config()
except Exception:
    pass
_attendance = AttendanceSystem()
_employees = EmployeeDatabase()
_reports = ReportGenerator(attendance=_attendance)


@api_bp.get("/cameras")
def list_cameras():
    cfg = _runner.config if _runner.config else _runner.load_config()
    return jsonify(cfg.get("cameras", []))


@api_bp.post("/cameras/<cid>/start")
def start_camera(cid: str):
    cfg = next((c for c in _runner.config.get("cameras", []) if c.get("id") == cid), None)  # type: ignore[attr-defined]
    if not cfg:
        return jsonify({"ok": False, "error": "camera not found"}), 404
    _runner.start_camera(cfg)
    return jsonify({"ok": True})


@api_bp.post("/cameras/<cid>/stop")
def stop_camera(cid: str):
    _runner.stop_camera(cid)
    return jsonify({"ok": True})


@api_bp.get("/employees")
def list_employees():
    return jsonify(_employees.list_all_employees())


@api_bp.post("/employees")
def add_employee():
    data: Dict[str, Any] = request.get_json(force=True)
    emp_id = data.get("emp_id")
    name = data.get("name")
    if not emp_id or not name:
        return jsonify({"ok": False, "error": "emp_id and name required"}), 400
    _employees.add_employee(emp_id, name, **{k: v for k, v in data.items() if k not in {"emp_id", "name"}})
    _employees.save()
    return jsonify({"ok": True})


@api_bp.get("/attendance/today")
def attendance_today():
    rows = _attendance.get_daily_attendance(date.today())
    return jsonify(rows)


@api_bp.get("/attendance/<emp_id>")
def attendance_by_emp(emp_id: str):
    rows = _attendance.get_employee_attendance(emp_id, start_date=date.today().isoformat(), end_date=date.today().isoformat())
    return jsonify(rows)


@api_bp.post("/reports/generate")
def api_generate_report():
    data = request.get_json(force=True)
    rtype = data.get("type", "daily")
    if rtype == "daily":
        d = data.get("date", date.today().isoformat())
        out = _reports.generate_daily_summary(d, Path("reports") / f"daily_{d}.csv")
        return jsonify({"ok": True, "path": out})
    return jsonify({"ok": False, "error": "unsupported type"}), 400


@api_bp.get("/stats/current")
def stats_current():
    today_rows = _attendance.get_daily_attendance(date.today())
    present = len({r["employee_id"] for r in today_rows if r.get("check_out_time") is None})
    cams_status = _runner.get_all_status()
    active_cams = sum(1 for s in cams_status.values() if s.get("running"))
    return jsonify({"present": present, "active_cams": int(active_cams)})
