"""
نظام صلاحيات بسيط قائم على الجلسات (Flask sessions) دون الاعتماد على إضافات.
الأدوار:
- admin: كل الصلاحيات
- manager: تقارير/حضور
- operator: التحكم بالكاميرات
- viewer: عرض فقط
"""
from __future__ import annotations

import functools
from typing import Callable, Optional

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

auth_bp = Blueprint("auth", __name__)

# مستخدمون تجريبيون (يجب استبدالها بنظام حقيقي/قاعدة بيانات في الإنتاج)
USERS = {
    "admin": {"password": "admin", "role": "admin"},
    "manager": {"password": "manager", "role": "manager"},
    "operator": {"password": "operator", "role": "operator"},
    "viewer": {"password": "viewer", "role": "viewer"},
}


def login_required(view: Optional[Callable] = None, *, role: Optional[str] = None) -> Callable:
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapped(*args, **kwargs):
            user = session.get("user")
            if not user:
                return redirect(url_for("auth.login", next=request.path))
            if role:
                roles_order = ["viewer", "operator", "manager", "admin"]
                user_role = session.get("role", "viewer")
                # السماح إذا كان دور المستخدم نفس الدور المطلوب أو أعلى (admin أعلى شيء)
                if roles_order.index(user_role) < roles_order.index(role):
                    flash("صلاحيات غير كافية", "danger")
                    return redirect(url_for("auth.login"))
            return fn(*args, **kwargs)
        return wrapped
    return decorator(view) if view else decorator


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        user = USERS.get(username)
        if user and user.get("password") == password:
            session["user"] = username
            session["role"] = user.get("role", "viewer")
            nxt = request.args.get("next") or url_for("dashboard")
            return redirect(nxt)
        else:
            flash("بيانات الدخول غير صحيحة", "danger")
    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
