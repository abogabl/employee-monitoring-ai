"""
REST API v1 - Fresh Start Stub Version
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request

api_bp = Blueprint("api_v1", __name__)


@api_bp.get("/cameras")
def list_cameras():
    """List cameras - stub"""
    return jsonify([])


@api_bp.post("/cameras/<cid>/start")
def start_camera(cid: str):
    """Start camera - stub"""
    return jsonify({"ok": False, "error": "Not implemented yet"}), 501


@api_bp.post("/cameras/<cid>/stop")
def stop_camera(cid: str):
    """Stop camera - stub"""
    return jsonify({"ok": False, "error": "Not implemented yet"}), 501


@api_bp.get("/employees")
def list_employees():
    """List employees - stub"""
    return jsonify([])


@api_bp.get("/attendance/today")
def today_attendance():
    """Today's attendance - stub"""
    return jsonify([])


@api_bp.get("/report/<kind>")
def generate_report(kind: str):
    """Generate report - stub"""
    return jsonify({"ok": False, "error": "Not implemented yet"}), 501


@api_bp.route("/status")
def api_status():
    """API Status check"""
    return jsonify({
        "status": "ok",
        "version": "1.0",
        "fresh_start": True
    })
